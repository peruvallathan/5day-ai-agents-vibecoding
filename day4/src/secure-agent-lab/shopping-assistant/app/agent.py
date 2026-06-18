# ruff: noqa
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

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

import os
import google.auth

# In-memory store for discount codes and their used status
DISCOUNT_CODES = {
    "WELCOME50": {"valid": True, "used_by": None},
    "SUMMER20": {"valid": True, "used_by": None},
}


def redeem_discount(user_id: str, code: str) -> str:
    """Redeems a single-use discount code for a registered user.

    Args:
        user_id: The ID of the registered user attempting to redeem the code.
        code: The discount code to redeem.

    Returns:
        A string indicating the success or failure of the redemption.
    """
    if not user_id:
        return (
            "Error: A valid registered user ID is required to redeem a discount code."
        )

    code_upper = code.upper()
    if code_upper not in DISCOUNT_CODES:
        return f"Error: The discount code '{code}' is invalid."

    code_data = DISCOUNT_CODES[code_upper]
    if not code_data["valid"] or code_data["used_by"] is not None:
        return f"Error: The discount code '{code}' has already been redeemed."

    # Mark as redeemed
    code_data["valid"] = False
    code_data["used_by"] = user_id

    return f"Success: Discount code '{code}' has been successfully redeemed for user '{user_id}'."


root_agent = Agent(
    name="shopping_assistant",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="You are an AI shopping assistant for a retail store. Help customers find products, answer questions, and assist with redeeming discount codes.",
    tools=[redeem_discount],
)

app = App(
    root_agent=root_agent,
    name="app",
)
