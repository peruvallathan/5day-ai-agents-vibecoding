# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
from app.agent import redeem_discount, DISCOUNT_CODES

@pytest.fixture(autouse=True)
def reset_discount_codes():
    """Fixture to reset the DISCOUNT_CODES dictionary before and after each test."""
    original_state = {
        "WELCOME50": {"valid": True, "used_by": None},
        "SUMMER20": {"valid": True, "used_by": None},
    }
    DISCOUNT_CODES.clear()
    for k, v in original_state.items():
        DISCOUNT_CODES[k] = v.copy()
    yield
    DISCOUNT_CODES.clear()
    for k, v in original_state.items():
        DISCOUNT_CODES[k] = v.copy()

def test_redeem_discount_success():
    """Verify that a valid user can redeem an unused discount code."""
    result = redeem_discount(user_id="user_123", code="WELCOME50")
    assert "Success" in result
    assert "successfully redeemed" in result
    assert DISCOUNT_CODES["WELCOME50"]["valid"] is False
    assert DISCOUNT_CODES["WELCOME50"]["used_by"] == "user_123"

def test_redeem_discount_case_insensitive():
    """Verify that discount codes are treated case-insensitively."""
    result = redeem_discount(user_id="user_123", code="welcome50")
    assert "Success" in result
    assert DISCOUNT_CODES["WELCOME50"]["valid"] is False

def test_redeem_discount_empty_user_id():
    """Verify that an empty user ID results in a validation failure."""
    result = redeem_discount(user_id="", code="WELCOME50")
    assert "Error" in result
    assert "valid registered user ID is required" in result
    assert DISCOUNT_CODES["WELCOME50"]["valid"] is True
    assert DISCOUNT_CODES["WELCOME50"]["used_by"] is None

def test_redeem_discount_invalid_code():
    """Verify that trying to redeem a non-existent code fails."""
    result = redeem_discount(user_id="user_123", code="INVALID99")
    assert "Error" in result
    assert "invalid" in result

def test_redeem_discount_already_redeemed():
    """Verify that a discount code cannot be redeemed more than once."""
    first_result = redeem_discount(user_id="user_123", code="WELCOME50")
    assert "Success" in first_result
    
    second_result = redeem_discount(user_id="user_456", code="WELCOME50")
    assert "Error" in second_result
    assert "already been redeemed" in second_result
    assert DISCOUNT_CODES["WELCOME50"]["used_by"] == "user_123"
