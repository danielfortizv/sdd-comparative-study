# Canonical Seed Specification - E-Commerce - Stage 2

## Purpose
Extend the existing Stage 1 e-commerce application with product reviews that support images and moderation. Preserve the existing catalog, cart, authentication, and simulated checkout behavior unless a reviewed specification change explicitly requires otherwise.

## Functional scope
- Users can submit reviews associated with a product.
- Reviews support attached images.
- Product reviews have a moderation workflow.
- Users can view the reviews made visible by moderation on the relevant product.

## Specification workflow
Inspect the inherited native specifications and implementation first. Generate Stage 2 native requirements, design, and tasks through the tool's specification workflow before changing application code. Keep Stage 1 artifacts identifiable and traceable.
The seed intentionally leaves review eligibility, rating fields, image limits and storage, moderation states, moderator identity/permissions, persistence, and edit/delete behavior undecided. The researcher delegates these choices to the tool. Choose simple, coherent local-demo defaults, document the assumptions in the native specs, and proceed without asking questions. Avoid external paid services.
Use the existing React/TypeScript frontend and Python/FastAPI backend. All prompts, specifications, code, comments, documentation, and UI text must be in English. Any code correction must follow a native specification change. Complete all native specification artifacts before implementing. The researcher authorizes implementation after specification generation and accepts reasonable variation between tools. Do not wait for human approval.

