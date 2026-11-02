"""Persist root's complete manual55-Say review; no inference-based question count."""
from kiro_research import DOCS, load, stamp, write
data=load(DOCS/'question-audit.json')
review=load(DOCS/'question-review.json',{})
row=next(r for r in data['runs'] if r['label']=='06-qa-retry')
assert len(row['natural_say_messages'])==55
assert not row['non_tool_approval_pending_interactions']
for message in row['natural_say_messages']:
    review[message['message_id']]={
        'is_blocking_clarification':False,
        'is_nonblocking_review_confirmation_reference':False,
        'reason':'Root read complete Say in two batches: progress/diagnostic explanation, version selection or result summary, with no actual researcher question or confirmation request. Technical rhetorical questions and cited requirements are not user requests. Native self-reported verification is independently audited.',
        'reviewed_at_utc':stamp(),
    }
write(DOCS/'question-review.json',review)
print('06:55 complete Say reviewed,0 blocking/0 nonblocking confirmations; no user_input interaction')
