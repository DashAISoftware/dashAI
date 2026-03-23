---
title: "Module Guide: Generative AI"
sidebar_label: Generative AI
sidebar_position: 3
---

# Module Guide: Generative AI

The Generative module enables you to interact with generative AI models through a chat-like interface. It supports text generation and image generation tasks.

## Generative Tasks

| Task | Description |
|------|-------------|
| TextToTextGenerationTask | Text generation, summarization, and transformation |
| TextToImageGenerationTask | Generate images from text prompts |
| ControlNetTask | Image generation with spatial control |

## Available Models

| Model | Task |
|-------|------|
| QwenModel | Text-to-text generation |
| StableDiffusionV2Model | Text-to-image generation |
| StableDiffusionV3Model | Text-to-image generation |
| StableDiffusionXLV1ControlNet | ControlNet image generation |

## Adjustable Parameters

- **Temperature** — Controls output diversity (higher = more varied)
- **Max Tokens** — Maximum length of the generated output
- Each parameter includes an info tooltip with a contextual explanation

## Session Management

- Create sessions with a name and description to organize your work
- The interaction history of each session is preserved
- You can modify parameters between interactions and observe the effect

:::note
Generative models require significant GPU memory. Ensure your hardware meets the minimum requirements before loading large models.
:::
