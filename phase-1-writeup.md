# Phase 1 write-up 

## Evaluation Set

### Task 1
Researchers and graduate students often maintain experiment logs or paper drafts in Markdown because it integrates easily with Git and keeps formatting lightweight. Tools like Typora and Obsidian allow quick export to PDF, which researchers frequently do to include experimental notes or appendices in a formal report. This workflow—writing Markdown, exporting it, and merging it with a report—is a real step in preparing deliverables or paper submissions in academic settings.

For ECUA evaluation, this task tests whether an agent can manage cross-application operations that require sequential reasoning: exporting through Typora, locating the output, and merging PDFs in PDF Arranger. It captures how well an edge agent handles GUI navigation, file-path operations, and state continuity, all without relying on cloud inference.

### Task 2
Researchers and educators often need to record and edit short audio clips—for example, to include an experiment explanation in a presentation, record a lab demonstration, or prepare dataset samples. The workflow of recording with GNOME Sound Recorder and editing with Audacity mirrors real open-source usage described in their official manuals and Linux community guides. It’s a standard, reproducible task in academic content creation.

This task challenges an ECUA to manage time-sensitive and multi-application steps: recording audio of fixed duration, trimming a waveform, and exporting to another format. Humans rely on visual and auditory cues for such operations, but a local agent must reason over timing, GUI state, and file conversion autonomously. It’s a compact yet realistic test of multimodal control under edge-device constraints.

### Task 3
This is common in troubleshooting: quickly sampling CPU-heavy processes and saving a short “burst” log for later inspection or to attach in tickets. Mirrors common SRE/dev workflows using `top` batch mode and `tee` with iteration/delay flags.

In this task, agent must time-boundedly capture output, and combine flags and redirection when using CLI.

### Task 5
Branding and presentation preparation often require pulling a logo from the web, cleaning it up, and integrating it into slides. The workflow of downloading an image, cropping and resizing in a raster editor (e.g., GIMP), and inserting it into a LibreOffice Impress slide mirrors a common academic/industry practice when assembling talk decks or course materials.

For ECUA evaluation, this task tests cross-application sequencing, visual operations (crop/resize), and correct asset placement inside a slide. It evaluates whether the agent can manage browser save locations, image editing parameters, and slide insertion with consistent file-path handling.

### Task 4
Resolving merge conflicts is a fundamental and daily task for anyone in software development or collaborative research using Git. Using a modern IDE like VS Code to visually identify the conflicting blocks, edit the file to incorporate the correct changes, and commit the resolution is a standard, real-world workflow. 

For ECUA evaluation, this task tests the agent's ability to perform complex, in-application reasoning within a single, sophisticated tool.

### Task 6
This task serves as a multi-app use case. It originates from some daily productivity use cases such as digitizing handwritten notes. It evaluates visual understanding (image-to-text), clipboard control, multi-application sequencing, and file export consistency. Besides, it also shows whether an agent can manage perception + action coherently.

### Task 7
Broken symbolic links are a common and frustrating problem in Linux-based environments, frequently encountered by developers, and researchers. These issues arise when a target file is moved, renamed, or deleted, causing any symlink pointing to it to fail and potentially breaking scripts or applications.

The process of identifying a broken link and then repairing it is a basic skill for any terminal user. This task is a pure test of the agent's proficiency in a Command Line Interface (CLI) environment.

### Task 8
Routine storage triage: finding large files for cleanup is a frequent personal-device task. The pipeline relies on GNU `find` to list file sizes and paths, sorted by size, then `numfmt` for human-readable units.

This tests agent's ability to restrict to files and handle subdirectories, path/quoting correctness, and multi-tool piping.

### Task 9
Data integrity checks are a core part of secure and reproducible workflows. Verifying a downloaded artifact’s SHA256 hash before organizing it reduces the risk of corrupted or tampered inputs and keeps workspaces tidy. This is routine for developers and researchers handling datasets, models, or installers.

For ECUA evaluation, this task measures CLI proficiency, correctness in computing and comparing checksums, and conditional organization of files based on verification results.

### Task 10
This task is inspired by bilingual writing workflows. It combines copy/paste, window focus management reading comprehension, and assesses whether the agent can integrate tool use with semantic understanding.

## Edge Environment
RTX 3090 24 GB VRAM 125 GB RAM 16 vCPUs
