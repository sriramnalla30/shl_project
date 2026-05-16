from pathlib import Path
from eval.parse_md_traces import parse_conversation, trace_to_eval_record

SAMPLE = """## Conversation
### Turn 1
**User**
> hi there
**Agent**
Welcome — could you tell me more?
_`end_of_conversation`: **false**_
### Turn 2
**User**
> personality test for a sales manager
**Agent**
Here is OPQ32r: <https://www.shl.com/products/product-catalog/view/opq/>
_`end_of_conversation`: **true**_
"""


def test_basic_parse():
    turns = parse_conversation(SAMPLE)
    assert len(turns) == 2
    assert turns[0]["user"] == "hi there"
    assert turns[1]["agent_urls"] == ["https://www.shl.com/products/product-catalog/view/opq"]
    assert turns[1]["end_of_conversation"] is True


def test_real_trace_parses():
    real = Path("sample_conversations/GenAI_SampleConversations/C1.md")
    if real.exists():
        rec = trace_to_eval_record(real)
        assert rec["id"] == "C1"
        assert len(rec["user_turns"]) >= 2
        assert len(rec["expected_urls"]) >= 1
