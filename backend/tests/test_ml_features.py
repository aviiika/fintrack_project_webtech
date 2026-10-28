"""Unit tests for text preprocessing — these can run without any ML dependencies."""
from app.ml.features.text_features import clean_batch, clean_description


def test_strips_long_reference_numbers():
    """Bank transaction IDs (6+ digits) should be removed as noise."""
    assert "414823910292" not in clean_description("UPI/414823910292/Zomato/payment")


def test_strips_upi_handles():
    """@okaxis, @paytm etc. are account routing — not merchant signal."""
    assert "@paytm" not in clean_description("zomato@paytm payment")


def test_strips_bank_codes():
    """UPI, NEFT, IMPS etc. appear everywhere — pure noise for classification."""
    cleaned = clean_description("UPI-ZOMATO NEFT CR")
    assert "upi" not in cleaned
    assert "neft" not in cleaned
    assert "zomato" in cleaned


def test_preserves_merchant_name():
    """The whole point: the merchant name must survive."""
    assert "zomato" in clean_description("UPI/XXX/Zomato Food/@paytm")


def test_handles_empty_input():
    assert clean_description("") == ""
    assert clean_description(None) == ""


def test_batch_returns_same_length():
    inputs = ["Zomato", "Swiggy", "Amazon"]
    assert len(clean_batch(inputs)) == 3
