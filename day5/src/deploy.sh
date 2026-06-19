#!/bin/bash
# =============================================================================
# deploy.sh — Full Day 5 deployment: Expense Agent + Manager Dashboard
# 5-Day AI Agents Intensive — Google × Kaggle
# =============================================================================
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud auth login)
#   - uv installed (https://docs.astral.sh/uv/)
#   - agents-cli installed (uvx google-agents-cli setup)
#   - PROJECT_ID set below
# =============================================================================

set -e

PROJECT_ID="YOUR_PROJECT_ID"
REGION="us-west1"

echo "════════════════════════════════════════"
echo " Step 1: Configure Google Cloud project"
echo "════════════════════════════════════════"
gcloud config set project $PROJECT_ID
gcloud auth application-default login

echo "Enabling required APIs..."
gcloud services enable \
  aiplatform.googleapis.com \
  cloudtrace.googleapis.com \
  cloudbuild.googleapis.com \
  agentregistry.googleapis.com \
  run.googleapis.com \
  pubsub.googleapis.com

echo "════════════════════════════════════════"
echo " Step 2: Deploy Expense Agent to Agent Runtime"
echo "════════════════════════════════════════"
cd expense-agent

# Install agents-cli and ADK skills
uvx google-agents-cli setup
agents-cli info

# Install dependencies
uv lock
agents-cli install

# Dry run before deploying
echo "Running dry-run..."
agents-cli deploy --dry-run

# Deploy to Agent Runtime (takes 5–10 min)
echo "Deploying to Agent Runtime (this takes 5–10 minutes)..."
agents-cli deploy --project $PROJECT_ID --region $REGION

# Get the Agent Runtime ID from deployment metadata
AGENT_RUNTIME_ID=$(python3 -c "import json; d=json.load(open('deployment_metadata.json')); print(d['agent_runtime_id'])")
echo "Agent Runtime ID: $AGENT_RUNTIME_ID"

echo "════════════════════════════════════════"
echo " Step 3: Test deployed agent"
echo "════════════════════════════════════════"
echo "Testing auto-approval ($50)..."
# (run via agents-cli test or Cloud Console Playground)

echo "════════════════════════════════════════"
echo " Step 4: Deploy Manager Dashboard to Cloud Run"
echo "════════════════════════════════════════"
cd ../submission_frontend

gcloud run deploy expense-manager-dashboard \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,AGENT_RUNTIME_ID=$AGENT_RUNTIME_ID,GOOGLE_CLOUD_REGION=$REGION"

# Grant dashboard service account access to Agent Runtime
DASHBOARD_SA=$(gcloud run services describe expense-manager-dashboard \
  --region=$REGION --format='value(spec.template.spec.serviceAccountName)')

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$DASHBOARD_SA" \
  --role="roles/aiplatform.user"

DASHBOARD_URL=$(gcloud run services describe expense-manager-dashboard \
  --region=$REGION --format='value(status.url)')
echo "Dashboard live at: $DASHBOARD_URL"

echo "════════════════════════════════════════"
echo " Step 5: Set up Pub/Sub event pipeline"
echo "════════════════════════════════════════"

# Create topics
gcloud pubsub topics create expense-reports
gcloud pubsub topics create expense-reports-dead-letter

# Create pubsub-invoker service account
gcloud iam service-accounts create pubsub-invoker \
  --display-name="Pub/Sub Expense Agent Invoker"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:pubsub-invoker@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Grant Pub/Sub service agent token creator
PUBSUB_SA="service-$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')@gcp-sa-pubsub.iam.gserviceaccount.com"
gcloud iam service-accounts add-iam-policy-binding \
  "pubsub-invoker@$PROJECT_ID.iam.gserviceaccount.com" \
  --member="serviceAccount:$PUBSUB_SA" \
  --role="roles/iam.serviceAccountTokenCreator"

# Agent Runtime :query endpoint
AGENT_RUNTIME_ENDPOINT="https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${REGION}/reasoningEngines/${AGENT_RUNTIME_ID}:query"

# Create push subscription (NoWrapper, OIDC auth, 10min ack, dead-letter)
gcloud pubsub subscriptions create expense-reports-push \
  --topic=expense-reports \
  --push-endpoint="$AGENT_RUNTIME_ENDPOINT" \
  --push-auth-service-account="pubsub-invoker@$PROJECT_ID.iam.gserviceaccount.com" \
  --push-no-wrapper \
  --ack-deadline=600 \
  --dead-letter-topic=expense-reports-dead-letter \
  --max-delivery-attempts=5

echo "════════════════════════════════════════"
echo " Step 6: Test end-to-end"
echo "════════════════════════════════════════"

echo "Publishing auto-approval test ($45)..."
gcloud pubsub topics publish expense-reports \
  --message='{"input": {"message": "{\"amount\": 45, \"submitter\": \"bob@company.com\", \"category\": \"meals\", \"description\": \"Team lunch\", \"date\": \"2026-06-04\"}"}}'

echo "Publishing HITL test ($250)..."
gcloud pubsub topics publish expense-reports \
  --message='{"input": {"message": "{\"amount\": 250, \"submitter\": \"alice@company.com\", \"category\": \"travel\", \"description\": \"NYC Flight Tickets\", \"date\": \"2026-06-04\"}"}}'

echo ""
echo "✅ All done!"
echo "Dashboard: $DASHBOARD_URL"
echo "Check Cloud Logging: gcloud logging read 'resource.type=\"aiplatform.googleapis.com/ReasoningEngine\"' --limit=20"
