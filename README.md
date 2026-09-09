# Ashwin Goyal

**I build intelligence a person can read, own and correct, and I measure what it costs.**

One question, approached from two sides. From the research side: how much of an agent can run with no model in the loop, on hardware people already have, and what does capability cost as you spend less? From the engineering side: how do you let an agent act, move money, sign, decide, and prove afterwards exactly why it did what it did?

## Current work

| Project | What it is | Evidence |
|---------|------------|----------|
| **[nyaya](https://github.com/let-the-dreamers-rise/nyaya)** | A benchmark for world models with cost as a scored column, and the dependency-free runtime at the $0 end of the curve. Learns an unseen game's rules on CPU and stores them as a page of Python you can read. | 249 tests, two corpora, every number regenerates from one command, held-out tables rebuilt by CI on every push. The losing rows are published: a one-line heuristic beats the learner, naive Bayes beats the readable rules, delegation is 2% today. [Site](https://let-the-dreamers-rise.github.io/nyaya/). |
| **[auto-evolve](https://github.com/let-the-dreamers-rise/auto-evolve)** | The spec nyaya's engine is built toward: skills compiled from experience, verified by replay so anyone holding the evidence can rescore them, inherited by the next agent. | Engine extracted from the ARC-AGI-3 work; archive and inheritance layers specified, not yet built. |

Everything below is earlier work on the engineering side of the same question. It is kept because it is real and shipped, not because it is the current focus.

---

## Earlier: agent authority and audit

---

## Agent governance and decision safety

The core thesis. Ten independent attempts at giving autonomous systems bounded authority and a defensible audit trail.

| Project | What it does | Live |
|---------|--------------|------|
| **clawshield** | Safety and reputation layer for agents that touch money - policy checks, transaction simulation, risk scoring, public audit trail | Mantle Turing Test 2026 |
| **kagi-vault** | Governed execution gateway. Secrets sealed server-side, policy decides what is allowed, authority revocable instantly | [live](https://kagi-vault.vercel.app) |
| **aura-decision-firewall** | Intercepts and risk-scores Web3 transactions before signing. Solidity on Mantle L2, 42 tests | [live](https://aura-decision-firewall.vercel.app) |
| **aura-cognitive-guardrail** | Decision Interruption System - halts high-risk actions before they become irreversible. Gemini 2.0 Flash + ElevenLabs | [live](https://aura-cognitive-guardrail.vercel.app) |
| **friction-sentinel-ai** | An autonomous judgment layer that decides when *not* to help. Google DeepMind Gemini 3 Hackathon | - |
| **economic-immune-system** | Agent that authorizes or rejects transactions against budget policy and risk. Gemini Pro + Circle Developer Controlled Wallets | - |
| **covenantos** | Multi-agent treasury OS. ERC-4337 smart accounts on Base, Arbitrum, TRON. On-chain policy commitments, signed receipts, MCP server | - |
| **agent-sla-engine** | On-chain SLA engine for agents - escrow, verifier staking, dispute resolution | [live](https://agent-sla-engine.vercel.app) |
| **approval-rationale-tracker** | Decision-memory for commercial loan portfolios. Keeps original approval logic visible and reviewable | [live](https://approval-rationale-tracker.vercel.app) |
| **decision-radar** | Decision intelligence for Jira. Captures *why* decisions were made, not just what changed | - |

---

## On-chain infrastructure

| Project | What it does | Live |
|---------|--------------|------|
| **proofflow** | Private revenue-based credit for emerging-market SMBs. Solana Anchor programs, Arcium MPC, Solana Attestation Service, USDC/CCTP | [proofflow.xyz](https://proofflow.xyz) |
| **foundry-0g** | Decentralized AI fine-tuning and licensing marketplace on 0G. OpenAI-compatible gateway with on-chain license gates and per-call receipts | [live](https://foundry-0g.vercel.app) |
| **squad-treasury** | Shared treasury agent - policy-gated spend, XMTP/Telegram approvals, x402 API purchases, Solana payouts, emergency revoke | [live](https://openwallet-web.vercel.app) |
| **genesis-solana-agent** | Autonomous root agent that creates and deploys new on-chain agents on Solana. Colosseum Agent Hackathon | - |
| **CREDA** | Creator Revenue Debt Architecture - tokenizing future creator income as an asset class. Solidity 0.8.24 | [live](https://creda-ecru.vercel.app) |
| **1TAPPAY** | One-tap Web3 payments on Etherlink L2. Next.js 15, Wagmi v2, Viem | [live](https://1-tappay.vercel.app) |

---

## Applied AI systems

| Project | What it does | Live |
|---------|--------------|------|
| **sentinel** | AI-native industrial safety command centre. Fuses sensor telemetry, permits, maintenance logs and regulatory circulars into a live Time-to-Incident clock | - |
| **Buildflow** | AI-native procurement for construction - RFQ drafting, quote comparison, PO generation. Gemini + Google Cloud, Next.js 16 | [live](https://buildflow-mu-neon.vercel.app) |
| **DEPTHGUARD** | Autonomous supply-chain threat agent. OSV/GitHub CVE data + Bright Data live web intelligence to catch threats pre-advisory | [live](https://depthguard-psi.vercel.app) |
| **nyaya-ai** | Converts court-order PDFs into source-linked, human-approved government action plans with ownership, deadlines and evidence trail | [live](https://nyaya-ai-tau.vercel.app) |
| **contract-proof** | API contract drift guard - detects breaking changes and remediates automatically. IBM Bob Hackathon | [live](https://contract-proof.vercel.app) |
| **wallet-rescue-ops** | OpenEnv incident-response environment for compromised crypto wallets. Meta PyTorch Hackathon 2026 | - |

---

## Stack

**Languages** TypeScript, Python, Solidity, Rust, JavaScript

**AI** Gemini (Pro / 2.0 Flash / 3), Google Cloud Vertex, ElevenLabs, PyTorch, MCP

**Chains** Solana (Anchor), Base, Arbitrum, Mantle, Etherlink, Creditcoin, 0G, TRON, ERC-4337 account abstraction

**Infra** Next.js, React, Hono, Postgres, Redis, Drizzle, Firebase, Cloud Run, Cloud SQL, Vercel, Docker

**Specialist** Arcium MPC, Solana Attestation Service, Circle Developer Controlled Wallets, USDC/CCTP, x402, XMTP, Privy passkeys

---

## Work with me

Available for contract work on agent governance, autonomous transaction safety, and on-chain infrastructure.

If you are shipping agents that touch money or take irreversible action and you need the guardrail, policy and audit layer built properly - that is the thing I have built ten times.

**Contact:** ashgoyal1990@gmail.com
