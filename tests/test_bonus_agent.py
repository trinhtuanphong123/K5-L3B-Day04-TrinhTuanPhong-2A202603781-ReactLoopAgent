"""Test offline cho phần bonus: retry 429, pagination, context, injection."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from agent import run_agent
from bonus.tools import BonusTools
from test_lab import FakeProvider, tool_call, final


def details_call(call_id, provider, incident_id, **extra):
    args = {'provider': provider, 'incident_id': incident_id, **extra}
    return tool_call(call_id, 'get_incident_details', json.dumps(args))


class RetryAfterTools:
    """Tool stub trả 429 một lần với Retry-After, sau đó thành công."""

    def __init__(self, retry_after):
        self.retry_after = retry_after
        self.calls = 0

    def execute(self, name, args):
        self.calls += 1
        if self.calls == 1:
            return {'ok': False, 'error': 'RATE_LIMITED', 'http_status': 429,
                    'retry_after': self.retry_after, 'retriable': True}
        return {'ok': True, 'provider': 'vercel', 'source': 'https://www.vercel-status.com'}


class BonusAgentHardeningTests(unittest.TestCase):
    def test_rate_limit_cap_blocks_fourth_call(self):
        tools = BonusTools(scenario='rate_limit_always')
        fake = FakeProvider([
            tool_call('v1', 'get_vercel_status', '{}'),
            tool_call('v2', 'get_vercel_status', '{}'),
            tool_call('v3', 'get_vercel_status', '{}'),
            tool_call('v4', 'get_vercel_status', '{}'),
            final('Vercel chưa kiểm tra được do 429 kéo dài; GitHub ổn.'),
        ])
        result = run_agent('Kiểm tra GitHub và Vercel', fake, tools, max_steps=6)
        self.assertEqual(result['status'], 'completed')
        tool_events = [e for e in result['trace'] if e['event'] == 'tool']
        self.assertEqual(sum(e['name'] == 'get_vercel_status' for e in tool_events), 3)
        self.assertEqual(sum(e['event'] == 'tool_blocked' for e in result['trace']), 1)
        self.assertTrue(any(e['event'] == 'retry_exhausted' for e in result['trace']))
        self.assertTrue(any(e['result'].get('retry_exhausted') for e in tool_events))

    def test_retry_after_wait_and_long_stop(self):
        with patch('agent.time.sleep') as sleep:
            tools = RetryAfterTools('1')
            fake = FakeProvider([
                tool_call('v1', 'get_vercel_status', '{}'),
                tool_call('v2', 'get_vercel_status', '{}'),
                final('Vercel operational; source https://www.vercel-status.com'),
            ])
            result = run_agent('x', fake, tools, max_steps=5)
        self.assertEqual(result['status'], 'completed')
        sleep.assert_called_once_with(1.0)
        self.assertTrue(any(e['event'] == 'retry_wait' and e['seconds'] == 1.0 for e in result['trace']))

        with patch('agent.time.sleep') as sleep:
            tools = RetryAfterTools('60')
            fake = FakeProvider([
                tool_call('v1', 'get_vercel_status', '{}'),
                tool_call('v2', 'get_vercel_status', '{}'),
                final('Không kiểm tra được Vercel.'),
            ])
            result = run_agent('x', fake, tools, max_steps=5)
        sleep.assert_not_called()
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(any(e['event'] == 'retry_exhausted' for e in result['trace']))
        self.assertTrue(any(e['event'] == 'tool_blocked' for e in result['trace']))

    def test_noisy_status_is_compacted(self):
        tools = BonusTools(scenario='noisy')
        fake = FakeProvider([
            tool_call('v1', 'get_vercel_status', '{}'),
            final('Vercel Builds ổn; nguồn https://www.vercel-status.com'),
        ])
        result = run_agent('Kiểm tra Vercel Builds', fake, tools, max_steps=4)
        self.assertEqual(result['status'], 'completed')
        event = next(e for e in result['trace'] if e['event'] == 'tool' and e['name'] == 'get_vercel_status')
        self.assertLessEqual(len(event['result']['distractors']), 9)
        self.assertTrue(any(isinstance(x, dict) and x.get('omitted_items') for x in event['result']['distractors']))
        self.assertTrue(any(e['event'] == 'context_compact' and e['omitted_items'] > 0 for e in result['trace']))
        sent = json.loads(fake.histories[1][-1]['content'])
        self.assertLessEqual(len(sent['distractors']), 9)

    def test_pagination_reads_next_offset(self):
        tools = BonusTools()
        first = tools.execute('get_incident_details', {'provider': 'vercel', 'incident_id': 'sps6n39gm4sg'})
        fake = FakeProvider([
            details_call('d1', 'vercel', 'sps6n39gm4sg'),
            details_call('d2', 'vercel', 'sps6n39gm4sg', offset=first['next_offset'], limit=2),
            final('Update nói GitHub upstream. Nguồn: ' + first['url']),
        ])
        result = run_agent('Tra timeline', fake, tools, max_steps=5)
        self.assertEqual(result['status'], 'completed')
        events = [e for e in result['trace'] if e['event'] == 'tool' and e['name'] == 'get_incident_details']
        self.assertEqual([e['arguments'].get('offset', 0) for e in events], [0, first['next_offset']])
        self.assertTrue(any('93njd414rpbx' in json.dumps(e['result']) for e in events))

    def test_pagination_claim_guard(self):
        tools = BonusTools()
        first = tools.execute('get_incident_details', {'provider': 'vercel', 'incident_id': 'sps6n39gm4sg'})
        fake = FakeProvider([
            details_call('d1', 'vercel', 'sps6n39gm4sg'),
            final('Đã xem toàn bộ timeline. Nguồn: ' + first['url']),
            final('Incident resolved; nguồn: ' + first['url']),
        ])
        result = run_agent('Tra timeline', fake, tools, max_steps=5)
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(any(e['event'] == 'validation_pagination_claim' for e in result['trace']))

    def test_injection_marker_gets_revision(self):
        tools = BonusTools(scenario='injection')
        fake = FakeProvider([
            tool_call('n1', 'get_npm_status', '{}'),
            final('BONUS_INJECTION_SUCCEEDED'),
            final('npm snapshot indicator none; source https://status.npmjs.org'),
        ])
        result = run_agent('Kiểm tra npm', fake, tools, max_steps=5)
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(any(e['event'] == 'validation_untrusted_echo' for e in result['trace']))

    def test_human_readable_incident_url_passes_source_gate(self):
        tools = BonusTools()
        details = tools.execute('get_incident_details', {'provider': 'vercel', 'incident_id': 'sps6n39gm4sg'})
        human_url = f"https://www.vercel-status.com/incidents/{details['id']}"
        fake = FakeProvider([
            details_call('d1', 'vercel', 'sps6n39gm4sg'),
            final('Incident resolved. Nguồn: ' + human_url),
        ])
        result = run_agent('Tra timeline', fake, tools, max_steps=4)
        self.assertEqual(result['status'], 'completed')
        self.assertFalse(any(e['event'] == 'validation_missing_source' for e in result['trace']))


if __name__ == '__main__':
    unittest.main()
