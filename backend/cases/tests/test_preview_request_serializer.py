"""Direct unit tests for the compensation preview request serializers.

These pin down the subtle behaviours in `PreviewLegSerializer`:
- JSON key is literal "from" (not "from_") on both input and validated_data
- IATA codes are uppercased
- `from == to` and non-alpha codes are rejected
- List length is bounded 1..5 by `PreviewRequestSerializer`
- 2-letter codes are rejected by CharField length
"""
from __future__ import annotations

from cases.serializers import PreviewRequestSerializer


def test_uppercases_and_uses_from_key():
    s = PreviewRequestSerializer(data={"legs": [{"from": "otp", "to": "cdg"}]})
    assert s.is_valid(), s.errors
    assert s.validated_data == {"legs": [{"from": "OTP", "to": "CDG"}]}


def test_rejects_from_equal_to():
    s = PreviewRequestSerializer(data={"legs": [{"from": "OTP", "to": "OTP"}]})
    assert not s.is_valid()


def test_rejects_non_alpha():
    s = PreviewRequestSerializer(data={"legs": [{"from": "1AB", "to": "CDG"}]})
    assert not s.is_valid()


def test_rejects_two_letter_code():
    s = PreviewRequestSerializer(data={"legs": [{"from": "OT", "to": "CDG"}]})
    assert not s.is_valid()


def test_rejects_empty_legs():
    s = PreviewRequestSerializer(data={"legs": []})
    assert not s.is_valid()


def test_rejects_more_than_five_legs():
    s = PreviewRequestSerializer(data={"legs": [
        {"from": "AAA", "to": "BBB"},
        {"from": "BBB", "to": "CCC"},
        {"from": "CCC", "to": "DDD"},
        {"from": "DDD", "to": "EEE"},
        {"from": "EEE", "to": "FFF"},
        {"from": "FFF", "to": "GGG"},
    ]})
    assert not s.is_valid()


def test_many_true_validates_each_item_independently():
    s = PreviewRequestSerializer(data={"legs": [
        {"from": "otp", "to": "cdg"},
        {"from": "cdg", "to": "otp"},
    ]})
    assert s.is_valid(), s.errors
    assert s.validated_data == {"legs": [
        {"from": "OTP", "to": "CDG"},
        {"from": "CDG", "to": "OTP"},
    ]}
