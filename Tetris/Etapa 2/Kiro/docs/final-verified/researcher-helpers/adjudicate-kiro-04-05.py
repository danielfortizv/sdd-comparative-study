"""Persist root's completed manual Say review for04 and interrupted05 only."""
from kiro_research import DOCS, load, stamp, write

audit = load(DOCS / 'question-audit.json')
review = load(DOCS / 'question-review.json', {})
counts = {}
for run in audit['runs']:
    if run['label'] not in {'04-implement', '05-qa'}:
        continue
    counts[run['label']] = len(run['natural_say_messages'])
    for message in run['natural_say_messages']:
        blocking = message['message_id'] == 'c665b7b8-2ba1-4d78-ad7d-7389f97040a8-say'
        reason = ('Root read the complete natural Say message: progress, code/spec explanation, diagnostic analysis or self-reported result; no actual request for researcher clarification. Claims in the content are independently audited, not accepted as proof.')
        if message['message_id'] == '7e5a43c1-8d1d-481d-af06-0c66797721cb-say':
            reason = 'Read complete Say: mentions an intention to ask about legacy schema, then explicitly retracts it using existing authorization and proceeds. No question or new human input is actually requested.'
        if blocking:
            reason = ('Read complete Say and linked native user_input toolu_bdrk_01NGHsSKaYGP3mPKAEqgTXvc: asks how to proceed with the multi-part correction. Count one workflow-scope confirmation, paired with the pending interaction rather than summed twice. The offered full end-to-end path was selected automatically under existing authorization; no new human message was received. This is not an unresolved gameplay requirement.')
        review[message['message_id']] = {
            'is_blocking_clarification': blocking,
            'is_nonblocking_review_confirmation_reference': False,
            'question_class': 'workflow_scope_confirmation' if blocking else None,
            'reason': reason, 'reviewed_at_utc': stamp(),
            'review_scope': 'Complete native Say content; excludes Reasoning/tool output; interrupted05 retained interval only',
        }
write(DOCS / 'question-review.json', review)
print({'manually_reviewed_messages': counts, 'blocking_workflow_confirmations': {'04-implement':0,'05-qa':1}})
