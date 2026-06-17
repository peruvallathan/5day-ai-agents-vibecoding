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

from __future__ import annotations

import os
from typing import Any, Literal

from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.workflow import START, Workflow, node
from google.genai import types
from pydantic import BaseModel, Field

# Auth: Gemini API key (codelab Option 1) or Vertex AI ADC (Option 2).
if os.environ.get("GEMINI_API_KEY"):
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
else:
    try:
        import google.auth

        _, project_id = google.auth.default()
        if project_id:
            os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
            os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
    except Exception:
        pass

model = Gemini(
    model="gemini-2.0-flash",
    retry_options=types.HttpRetryOptions(attempts=5, initial_delay=2),
)


class InquiryCategory(BaseModel):
    category: Literal["shipping", "unrelated"] = Field(
        description=(
            "Determine if the user query is related to shipping (rates, tracking,"
            " delivery times, returns) or unrelated."
        )
    )


def save_query(node_input: types.Content) -> Event:
    """Saves user query in state for downstream nodes."""
    query = ""
    if node_input and node_input.parts:
        for part in node_input.parts:
            if part.text:
                query += part.text
    return Event(
        output=query,
        actions=EventActions(state_delta={"user_query": query}),
    )


categorize_agent = LlmAgent(
    name="categorize",
    model=model,
    instruction="You are an expert classifier. Categorize the user query.",
    output_key="inquiry_category",
    output_schema=InquiryCategory,
)


@node
def route_inquiry(ctx: Context, node_input: Any):
    """Routes the workflow based on the classified category."""
    category_data = ctx.state.get("inquiry_category", {})
    if isinstance(category_data, InquiryCategory):
        category = category_data.category
    else:
        category = category_data.get("category", "unrelated")
    query = ctx.state.get("user_query", "")
    yield Event(output=query, actions=EventActions(route=category))


faq_agent = LlmAgent(
    name="shipping_faq",
    model=model,
    instruction="""You are a customer support representative for a shipping company. Answer user questions based ONLY on the shipping FAQ below. Do not answer questions outside of the FAQ.

    SHIPPING FAQ:
    - Rates: Standard shipping is $5.99. Express shipping is $12.99. Orders
      over $50 qualify for free standard shipping.
    - Tracking: You can track your order by entering your tracking number on
      our website's tracking page.
    - Delivery Times: Standard delivery takes 3-5 business days. Express
      delivery takes 1-2 business days.
    - Returns: We offer free returns within 30 days of delivery. Please make
      sure the item is in its original condition.
    """,
)


@node
def handle_unrelated(ctx: Context, node_input: Any):
    """Handles unrelated inquiries politely."""
    decline_message = (
        "I am sorry, I am a shipping customer support assistant and can only"
        " answer questions related to our shipping FAQ."
    )
    yield Event(
        content=types.Content(
            role="model", parts=[types.Part.from_text(text=decline_message)]
        ),
        output=decline_message,
    )


root_agent = Workflow(
    name="customer_support_workflow",
    edges=[
        (START, save_query),
        (save_query, categorize_agent),
        (categorize_agent, route_inquiry),
        (
            route_inquiry,
            {"shipping": faq_agent, "unrelated": handle_unrelated},
        ),
    ],
)

app = App(
    name="app",
    root_agent=root_agent,
)
