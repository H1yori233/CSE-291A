# Phase 1 write-up 

## Evaluation Set

### Task 1
Researchers and graduate students often maintain experiment logs or paper drafts in Markdown because it integrates easily with Git and keeps formatting lightweight. Tools like Typora and Obsidian allow quick export to PDF, which researchers frequently do to include experimental notes or appendices in a formal report. This workflow—writing Markdown, exporting it, and merging it with a report—is a real step in preparing deliverables or paper submissions in academic settings.

For ECUA evaluation, this task tests whether an agent can manage cross-application operations that require sequential reasoning: exporting through Typora, locating the output, and merging PDFs in PDF Arranger. It captures how well an edge agent handles GUI navigation, file-path operations, and state continuity, all without relying on cloud inference.

### Task 2
Researchers and educators often need to record and edit short audio clips—for example, to include an experiment explanation in a presentation, record a lab demonstration, or prepare dataset samples. The workflow of recording with GNOME Sound Recorder and editing with Audacity mirrors real open-source usage described in their official manuals and Linux community guides. It’s a standard, reproducible task in academic content creation.

This task challenges an ECUA to manage time-sensitive and multi-application steps: recording audio of fixed duration, trimming a waveform, and exporting to another format. Humans rely on visual and auditory cues for such operations, but a local agent must reason over timing, GUI state, and file conversion autonomously. It’s a compact yet realistic test of multimodal control under edge-device constraints.

### Task 6
This task serves as a multi-app use case. It originates from some daily productivity use cases such as digitizing handwritten notes. It evaluates visual understanding (image-to-text), clipboard control, multi-application sequencing, and file export consistency. Besides, it also shows whether an agent can manage perception + action coherently.

### Task 10
This task is inspired by bilingual writing workflows. It combines copy/paste, window focus management reading comprehension, and assesses whether the agent can integrate tool use with semantic understanding.

## Edge Environment
RTX 3090 24 GB VRAM 125 GB RAM 16 vCPUs
