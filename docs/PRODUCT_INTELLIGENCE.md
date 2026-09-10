# LM-Screen Product Intelligence Timeline

## Overview
The Product Intelligence Timeline tracks historical changes in net quantity, MRP, manufacturer details, and statutory declarations across batches over time.

## Objective Framing
Changes across historical batches are labelled objectively as:
`Change detected — Requires Review`
The system does **NOT** automatically declare historical pack size changes as illegal or non-compliant.

## API Endpoint
`GET /api/v1/products/{product_id}/timeline`
Returns chronologically ordered timeline events with detected declaration shifts.
