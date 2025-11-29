# OSWorld / OSWorld-Human 分析总结

- **OSWorld Benchmark:** OSWorld is a NeurIPS 2024 benchmark of 369 open-ended computer tasks performed in a real OS environment (Ubuntu VM)[mlsys.wuklab.io](https://mlsys.wuklab.io/posts/oshuman/#:~:text=Based on our observations%2C we,source). Each task is defined by a JSON template with fields:

  - **`id`** – a unique identifier (usually a UUID) for traceability[blog.csdn.net](https://blog.csdn.net/gitblog_00281/article/details/153383094#:~:text=* 唯一标识：通过 `id `字段确保用例可追溯（如示例中的 `3c8f201a,表示需GIMP图像编辑器与操作系统协同）).
  - **`instruction`** – a natural language description of the task goal, possibly multi-step (e.g. *"Download an image from a URL, then compress it to under 600KB using GIMP"*[blog.csdn.net](https://blog.csdn.net/gitblog_00281/article/details/153383094#:~:text=)).
  - **`related_apps`** – a list of applications involved, used to ensure those apps are available/started in the VM (e.g. `["gimp", "os"]` for a task needing GIMP and OS file manager)[blog.csdn.net](https://blog.csdn.net/gitblog_00281/article/details/153383094#:~:text=* 唯一标识：通过 `id `字段确保用例可追溯（如示例中的 `3c8f201a,表示需GIMP图像编辑器与操作系统协同）).
  - **`config`** – optional preconditioning steps to execute *before* the agent starts (e.g. opening a terminal or loading a file). It’s an array of actions (like script commands) that set up the initial state[blog.csdn.net](https://blog.csdn.net/gitblog_00281/article/details/153383094#:~:text=). In the example, a config step of type `"execute"` triggers a keyboard shortcut (`ctrl+alt+t`) to open a terminal[blog.csdn.net](https://blog.csdn.net/gitblog_00281/article/details/153383094#:~:text={ ,).
  - **`evaluator`** – specifies how to automatically evaluate success. It typically includes:
    - a **`func`** name mapping to an evaluation function (e.g. `check_image_size`) defined in OSWorld’s `desktop_env/evaluators/metrics` modules[blog.csdn.net](https://blog.csdn.net/gitblog_00281/article/details/153383094#:~:text=模板系统的核心创新在于将评估逻辑与任务描述解耦，通过 ),
    - a **`result`** definition of what output to examine (e.g. a file path in the VM to check)[blog.csdn.net](https://blog.csdn.net/gitblog_00281/article/details/153383094#:~:text=),
    - an **`expected`** condition or threshold for success (e.g. maximum file size = 600000 bytes)[blog.csdn.net](https://blog.csdn.net/gitblog_00281/article/details/153383094#:~:text=,). When the agent signals it is **DONE**, the environment will run this evaluator to judge success/failure.
  - *(Note:* Newer versions of OSWorld also describe tasks in terms of `environment`, `success_criteria`, etc. – but the above reflects the core fields used in the original benchmark[blog.csdn.net](https://blog.csdn.net/gitblog_00219/article/details/153380742#:~:text=字段名 类型 描述 示例 ,path).)

- **DesktopEnv Interface:** OSWorld provides a `DesktopEnv` class managing the VM and task execution loop[GitHub](https://github.com/tylerelyt/test_bed/blob/6448e3f7d1bbdefcb4354e4ab79eec9c175bf941/docs/GUI_AGENT_GUIDE.md#L102-L109). Key methods include:

  - **`reset(task_config)`** – Launches or resets the VM to a clean state, loads required applications (`related_apps`), applies the `config` steps (if any), then returns the initial **observation** (the agent’s perception of the screen) along with the task `instruction`[GitHub](https://github.com/tylerelyt/test_bed/blob/6448e3f7d1bbdefcb4354e4ab79eec9c175bf941/docs/GUI_AGENT_GUIDE.md#L134-L143). After reset, the task’s GUI is ready for the agent.
  - **`step(action)`** – Takes an action from the agent (either a high-level action or executable code), executes it in the VM (e.g. moving the mouse and clicking), then captures the next observation. It returns a tuple `(obs, reward, done, info)` similar to OpenAI Gym:
    - `obs` is the new observation after the action,
    - `reward` is typically `1.0` if the action was `DONE` (task completed successfully) and `0.0` otherwise[GitHub](https://github.com/tylerelyt/test_bed/blob/6448e3f7d1bbdefcb4354e4ab79eec9c175bf941/docs/GUI_AGENT_GUIDE.md#L164-L169),
    - `done` is `True` if the agent signaled termination (`DONE` or `FAIL`) or if a maximum step count is reached,
    - `info` carries extra info (e.g. error messages if an action failed to execute).
  - **`get_observation()`** – (Internally used) Captures the current state from the VM. Depending on configuration, this may include a screenshot image, the accessibility tree, etc.
  - **`evaluate()`** – After a `DONE` action, the environment will run the specified evaluator function to determine success. This typically populates the final `reward` or success metric and logs the result.

- **Observation Types:** OSWorld offers multiple observation modalities for the agent, each with pros and cons:

  - **Screenshot** (`"screenshot"`): A full-image observation of the screen (e.g. 1920×1080 PNG). This provides all visual information (layout, colors, icons, text as rendered) to a Vision-Language Model (VLM)[arxiv.org](https://arxiv.org/html/2411.02391v1#:~:text=Attacking Vision,). Advantage: it’s the most faithful representation of the UI. Drawback: the agent must rely on vision (OCR, visual parsing) to interpret text or locate small UI elements, which can be challenging and token-inefficient for LLMs. Precise coordinate decisions from raw pixels are difficult for language models, especially smaller ones.
  - **Accessibility Tree** (`"a11y_tree"`): A serialized UI tree (in XML or a linearized text table) of the current window’s accessible UI elements[medium.com](https://medium.com/@techsachin/benchmarking-multimodal-agents-for-open-ended-tasks-in-real-computer-environments-ef338142c9c1#:~:text=For the use of webpage's,via ATSPI 2 on). This is obtained via the OS’s accessibility APIs (AT-SPI for Ubuntu) and lists GUI components with their attributes (e.g. role, name/text, bounding box coordinates)[GitHub](https://github.com/SunzeY/SEAgent/blob/c8887f157352494953b3317047929cf81465defa/OSWorld/mm_agents/agent.py#L85-L94)[GitHub](https://github.com/SunzeY/SEAgent/blob/c8887f157352494953b3317047929cf81465defa/OSWorld/mm_agents/agent.py#L105-L113). Advantage: It provides structured, textual information (e.g. button labels, fields text) directly to the LLM, making it easier to identify elements by name. It’s also usually more compact than an image. Drawback: It lacks visual context (the model doesn’t *“see”* the layout or appearance) and may include many irrelevant nodes. The model might struggle with spatial reasoning using text coordinates alone. Also, not all visual content (e.g. images or canvas drawings) is represented in a11y data.
  - **Set-of-Mark (SoM)** (`"som"`): A *hybrid* observation that combines visual and structural info. The environment (or agent) renders the screenshot with **bounding boxes and unique tags/IDs** over important UI elements[GitHub](https://github.com/SunzeY/SEAgent/blob/c8887f157352494953b3317047929cf81465defa/OSWorld/mm_agents/agent.py#L119-L127), effectively “marking” each interactive component. For example, a button might be labeled “A3” on the image. A corresponding list of elements with their tag IDs and descriptions may be provided (e.g. *“A3: Submit Button”*). The agent’s VLM thus sees a screenshot annotated with tags, and can refer to those tags in its output. Advantage: This enables precise GUI grounding – the model can identify an element by tag (visually and/or from a provided list) and produce a targeted action (e.g. *click A3*). This greatly reduces coordinate guesswork, since the actual coordinates for tag A3 are known to the environment[GitHub](https://github.com/SunzeY/SEAgent/blob/c8887f157352494953b3317047929cf81465defa/OSWorld/mm_agents/agent.py#L120-L128). Drawback: The tags and boxes might occlude parts of the image, and an extra mapping step (Grounding) is needed to convert tags to coordinates. Also, the model must be instructed properly on how to use the tags (it needs to output the tag identifier rather than free-form description).
  - **Combined** (`"screenshot_a11y_tree"`): Both an image and a textual a11y summary are given (this was used in some baselines with GPT-4V)[openreview.net](https://openreview.net/forum?id=tN61DTr4Ed&referrer=[the profile of Tao Yu](%2Fprofile%3Fid%3D~Tao_Yu5)#:~:text=For our settings with both,1] has also). This offers the richness of visual input with the clarity of text. The downside is high token overhead (image + lengthy text) and the need for the model to integrate both modalities. In practice, the SoM approach is a more structured way to combine modalities (by embedding structural info into the image via tags). Notably, one study found providing a screenshot and a11y together outperformed using a tagged screenshot in some cases[papers.nips.cc](https://papers.nips.cc/paper_files/paper/2024/file/5d413e48f84dc61244b6be550f1cd8f5-Paper-Datasets_and_Benchmarks_Track.pdf#:~:text=,a11y tree inputs%2C which), likely because the text detail from the a11y tree complemented the raw image. Thus, there’s a trade-off in design: one might even supply both the tagged image and a brief text list of tags for completeness.

- **Action Space – PyAutoGUI vs. Computer_13:** OSWorld defines what actions the agent can take:

  - **PyAutoGUI (unconstrained code):** In this mode, the agent outputs one or more lines of Python code (using the PyAutoGUI library) to perform the desired UI operation[GitHub](https://github.com/tylerelyt/test_bed/blob/6448e3f7d1bbdefcb4354e4ab79eec9c175bf941/docs/GUI_AGENT_GUIDE.md#L50-L58). For example: `pyautogui.moveTo(100, 200); pyautogui.click();` to click at (100,200). This is very expressive – any GUI operation can be done by some combination of moves, clicks, key presses, etc. – and it was the primary action space used in the OSWorld paper because it “saves tokens for describing action space” (the code is fairly concise)[papers.nips.cc](https://papers.nips.cc/paper_files/paper/2024/file/5d413e48f84dc61244b6be550f1cd8f5-Paper-Datasets_and_Benchmarks_Track.pdf#:~:text=,for describing action space). However, having the LLM generate code introduces complexity: the model must get syntax exactly right. Mistakes in code (syntax errors or incorrect use of API) could cause execution failures. Also, code generation might use a lot of tokens if each step requires multiple lines (though the prompt urged the model to be time-efficient and include delays appropriately[GitHub](https://github.com/tylerelyt/test_bed/blob/6448e3f7d1bbdefcb4354e4ab79eec9c175bf941/docs/GUI_AGENT_GUIDE.md#L50-L58)). PyAutoGUI actions are ultimately translated to low-level events (mouse move, click, type) by the environment.
  - **Computer_13 (structured actions):** This is a predefined set of 13 atomic GUI actions covering all basic mouse/keyboard operations[papers.nips.cc](https://papers.nips.cc/paper_files/paper/2024/file/5d413e48f84dc61244b6be550f1cd8f5-Paper-Datasets_and_Benchmarks_Track.pdf#:~:text=We implement two kinds of,for describing action space). For example, this set includes actions like **MOVE_CURSOR**, **LEFT_CLICK**, **RIGHT_CLICK**, **DOUBLE_CLICK**, **DRAG_AND_DROP**, **SCROLL_UP/DOWN**, **TYPE** (text entry), **PRESS_KEY** (single key like “Enter” or “Esc”), **HOTKEY** (combo like Ctrl+C), etc. Essentially, it’s a high-level API for GUI control. Instead of writing code, the agent outputs a JSON or dict specifying the action type and necessary parameters (coordinates, key values, text strings, etc.). The environment interprets this and executes the corresponding low-level events. *E.g.* an action might be represented as `{"action": "LEFT_CLICK", "target": [x, y]}` for clicking at a coordinate, or `{"action": "TYPE", "text": "Hello"}` to type text. This structured space removes the burden of syntax from the model – it just needs to choose the correct action type and target. It also makes parsing the model’s output easier (no need to execute code directly). The drawback is a slight loss of flexibility (the model must fit its solution into the 13 predefined acts, though they are general enough) and potentially more tokens to specify an action in JSON vs a short code line. In practice, Computer_13 covers everything needed for OSWorld tasks (it was used in subsequent research like OS-MAP[papers.nips.cc](https://papers.nips.cc/paper_files/paper/2024/file/5d413e48f84dc61244b6be550f1cd8f5-Paper-Datasets_and_Benchmarks_Track.pdf#:~:text=We implement two kinds of,for describing action space)). OSWorld baseline agents primarily used PyAutoGUI historically, but the Computer_13 space is increasingly used to simplify model output parsing and ensure safety (no arbitrary code execution).
  - **Special Actions:** In both modes, the agent can output special signals: **`WAIT`** (to do nothing but wait a bit – useful if an app is loading), **`DONE`** (to declare the task completed successfully), or **`FAIL`** (to give up if it’s stuck). These are not physical UI actions but control signals recognized by the environment[GitHub](https://github.com/tylerelyt/test_bed/blob/6448e3f7d1bbdefcb4354e4ab79eec9c175bf941/docs/GUI_AGENT_GUIDE.md#L56-L64). For example, returning `"WAIT"` causes the environment to simply pause briefly (and perhaps return an unchanged observation), whereas `"DONE"` will trigger the evaluator to check success[GitHub](https://github.com/tylerelyt/test_bed/blob/6448e3f7d1bbdefcb4354e4ab79eec9c175bf941/docs/GUI_AGENT_GUIDE.md#L164-L169). Agents are encouraged to use `DONE` only when the goal is achieved, and `FAIL` if they believe continuing is futile (this can mitigate penalties, as explained next).

- **OSWorld-Human Benchmark:** OSWorld-Human is an extension that incorporates **human reference trajectories** and efficiency metrics[GitHub](https://github.com/WukLab/wuklab_sysml/blob/c99af641fbb403cb61df1ce74181bf9b90f6cda7/content/posts/oshuman.md#L30-L38)[mlsys.wuklab.io](https://mlsys.wuklab.io/posts/oshuman/#:~:text=Based on our observations%2C we,source). Researchers manually executed all 369 OSWorld tasks and recorded the minimal or optimal sequence of actions a proficient human user took to complete each task[GitHub](https://github.com/WukLab/wuklab_sysml/blob/c99af641fbb403cb61df1ce74181bf9b90f6cda7/content/posts/oshuman.md#L30-L38). This provides a ground truth for the *necessary number of steps* and a *natural ordering of actions* for each task. The human trajectories serve two purposes:

  1. **Efficiency Reference:** They allow calculation of the **Weighted Efficiency Scores** (WES) for an agent’s run[mlsys.wuklab.io](https://mlsys.wuklab.io/posts/oshuman/#:~:text=To measure the performance of,agent’s accuracy by its efficiency). Specifically:
     - **WES⁺ (for successful tasks)** – measures how close the agent’s step count *tₐ* is to the human step count *tₕ*. It’s defined as *tₕ / tₐ*[mlsys.wuklab.io](https://mlsys.wuklab.io/posts/oshuman/#:~:text=Successful Task%3A %24r_t %3D 1%24). An agent that uses exactly as many steps as a human gets WES⁺ = 1.0 (100%), while using more steps yields a fraction <1.0. Fewer steps than human (>100%) is possible in theory (if the agent finds a shortcut), but in practice SOTA agents often take 1.4× to 2.7× human steps (WES⁺ ~0.7 down to ~0.37)[mlsys.wuklab.io](https://mlsys.wuklab.io/posts/oshuman/#:~:text=We analyze 16 agents’ performance,time latency)[github.com](https://github.com/WukLab/osworld-human#:~:text=Agent ,0.16).
     - **WES⁻ (for failed tasks)** – gives a small penalty based on how long the agent struggled before failing. It’s defined as -*tₐ / S* (where S is the max allowed steps)[mlsys.wuklab.io](https://mlsys.wuklab.io/posts/oshuman/#:~:text=Failed Task%3A %24r_t %3D 0%24). Failing immediately (in 1 step) would yield about -0.02 if S=50 (a minor penalty), whereas failing after using all 50 steps gives -1.0[mlsys.wuklab.io](https://mlsys.wuklab.io/posts/oshuman/#:~:text=Failed Task%3A %24r_t %3D 0%24). This encourages agents to not drag on hopeless attempts: failing fast is “less bad” than failing after a lengthy attempt.
     - These metrics combine **accuracy and efficiency**. An agent that is very accurate but very slow will have a moderate WES⁺, and an agent that is fast but fails often will suffer in accuracy and WES overall. OSWorld-Human thus highlights a Pareto trade-off between success rate and efficiency.
  2. **Grouped-action Trajectories:** The human demos revealed that certain sequences of GUI actions can be grouped without needing intermediate observations[GitHub](https://github.com/WukLab/wuklab_sysml/blob/c99af641fbb403cb61df1ce74181bf9b90f6cda7/content/posts/oshuman.md#L34-L42). For example, *clicking a text box, typing a word, and pressing Enter* – a human does this fluidly as one logical step. For an agent, these are typically three separate steps with three screenshots, but the intermediate screenshots might not be necessary (the screen doesn’t significantly change until after pressing Enter). OSWorld-Human defines **single-action vs. grouped-action** trajectories: the latter condense consecutive actions that a human would do in one go[GitHub](https://github.com/WukLab/wuklab_sysml/blob/c99af641fbb403cb61df1ce74181bf9b90f6cda7/content/posts/oshuman.md#L34-L42). Evaluating agents on grouped-action WES⁺ is even stricter – it compares agent steps to a potentially smaller human step count (since multiple human actions might count as 1 grouped step)[GitHub](https://github.com/WukLab/wuklab_sysml/blob/c99af641fbb403cb61df1ce74181bf9b90f6cda7/content/posts/oshuman.md#L34-L42). This motivates agents to *group trivial actions* and avoid needless “over-observing.”

  - **Takeaway:** OSWorld-Human emphasizes that today’s agents, while capable, are **much slower than humans**. A task taking a human 2 minutes might take an agent 20+ minutes due to repetitive observation and planning cycles[GitHub](https://github.com/WukLab/wuklab_sysml/blob/c99af641fbb403cb61df1ce74181bf9b90f6cda7/content/posts/oshuman.md#L16-L24). Even the best agent (Agent S2) used ~1.4× the human steps on average[mlsys.wuklab.io](https://mlsys.wuklab.io/posts/oshuman/#:~:text=We analyze 16 agents’ performance,time latency), and many others use 2× or more[github.com](https://github.com/WukLab/osworld-human#:~:text=Agent ,0.16). The main bottleneck identified is the latency from large-model calls at each step (especially when each step’s prompt includes the entire interaction history)[GitHub](https://github.com/WukLab/wuklab_sysml/blob/c99af641fbb403cb61df1ce74181bf9b90f6cda7/content/posts/oshuman.md#L26-L32). This insight strongly influences how we design our agent’s architecture for efficiency.

- **Implications for Agent Design:** To perform well on OSWorld and OSWorld-Human, an agent needs a **combination of capabilities**:

  - *Vision & Text Understanding:* It must interpret screenshots (identify icons, read text on the screen) and/or parse structured UI data. For instance, recognizing a “Save” button either via its icon or label.
  - *GUI Grounding:* It should map high-level intents (like *“click the Submit button”*) to precise GUI coordinates or element identifiers. This involves spatial reasoning (where is the element on screen?) and using available cues (a11y info, SoM tags) to avoid random clicking. High grounding precision reduces trial-and-error steps.
  - *Task Planning:* Many tasks are multi-step (e.g. *“Download a file, then edit it, then email it”* involves several applications). The agent must break down the instruction into sub-goals and plan a sequence of actions. A good plan prevents wandering or redundant actions, directly affecting step count (efficiency)[mlsys.wuklab.io](https://mlsys.wuklab.io/posts/oshuman/#:~:text=Successful Task%3A %24r_t %3D 1%24). Planning can be done upfront (at the start) or incrementally, but must be coherent.
  - *Memory:* The agent should remember past observations and actions (what has been done, what is left to do). Memory could be as simple as keeping the last screenshot in context or as complex as summarizing the entire interaction. Without memory, the agent might repeat actions or lose track of the goal, wasting steps.
  - *Action Abstraction & Grouping:* The agent should recognize when multiple primitive actions can be combined. For example, typing a full word can be treated as one high-level action rather than letter-by-letter decisions. Grouping such actions (when safe) means fewer overall reasoning loops, improving WES. Human references highlight where this is possible[GitHub](https://github.com/WukLab/wuklab_sysml/blob/c99af641fbb403cb61df1ce74181bf9b90f6cda7/content/posts/oshuman.md#L34-L42).
  - *Reflection & Adaptation:* If the agent is not making progress (e.g. tries the wrong approach repeatedly), it should detect this and **reflect** on its strategy. This might involve analyzing why the current plan isn’t working and revising it. However, reflection should be used judiciously – it’s essentially an expensive planning step mid-task. The OSWorld-Human analysis shows doing this too often (or every step) can bog the agent down in thought, leading to huge latency[GitHub](https://github.com/WukLab/wuklab_sysml/blob/c99af641fbb403cb61df1ce74181bf9b90f6cda7/content/posts/oshuman.md#L26-L32). The agent needs a mechanism to occasionally pause and re-plan, but without incurring large overhead each step.
  - *Termination Judgment:* Knowing when to hit DONE (after success) or FAIL (if truly stuck) is important. A fast failure can save time (and WES penalty) relative to a drawn-out failure[mlsys.wuklab.io](https://mlsys.wuklab.io/posts/oshuman/#:~:text=Failed Task%3A %24r_t %3D 0%24). Conversely, recognizing success criteria from observation is crucial to stop as soon as the goal is achieved (e.g. noticing “Mission accomplished” text or a file appearing in the correct folder).

  These competencies guide the architecture design. In summary, our agent must intelligently perceive the UI, ground its actions accurately, plan its moves efficiently (with minimal repeated thinking), and adapt when needed – all while interfacing properly with the OSWorld environment.

## Agent 总体架构设计

Leveraging the **Agent-S** framework concept (a modular agent with a *Supervisor/Planner*, *Sub-agents or Specialists*, and memory) as inspiration, we propose a simplified multi-module architecture tailored for a single Qwen-3 VL 8B model. The design focuses on minimizing expensive calls and achieving precise GUI manipulation. The major components and their interactions are:



- **High-Level Planner (Manager):** This module is responsible for high-level task understanding and decomposition. It is invoked **infrequently** – typically at the start of a task, and optionally if the agent is stuck. On task start, the Planner takes the user instruction and (optionally) the initial observation, and produces a *plan*: a sequence of sub-goals or steps to accomplish the task. For example, given a complex instruction, it might output: *“1) Open Chrome and navigate to example.com, 2) Download the file, 3) Open the file in LibreOffice, 4) Save as PDF.”* This plan serves as a roadmap so the agent doesn’t constantly re-figure the overall goal. The Manager may also monitor progress: if many steps have passed with little headway (or a misalignment with the plan), it can trigger a re-planning or reflection. **Call frequency:** ideally once at the start (to avoid overhead each step) – this aligns with OSWorld-Human’s lesson to reduce per-step planning latency[GitHub](https://github.com/WukLab/wuklab_sysml/blob/c99af641fbb403cb61df1ce74181bf9b90f6cda7/content/posts/oshuman.md#L26-L32). Only when necessary (e.g. nearing step limit or repeated failure), the Manager can be consulted again to adjust the plan (like Agent-S’s reflective “S3” cycle). By limiting these calls, we trade a bit of upfront thinking for much faster execution of each step.
- **Step Executor (Decider):** This is the per-step decision-making module that chooses the next concrete action(s) based on the current observation and the plan. It corresponds to the “Agent” loop that does Observe->Act. The Executor is essentially the Qwen VL model prompted with the latest state (and possibly a summary of recent history and the current plan context). At each iteration, it outputs 1 to 3 low-level actions to execute. We allow multiple actions if they are logically grouped (e.g. click a textbox *and then* type text into it). Grouping such actions into one step can reduce the total number of reasoning loops, improving efficiency (targeting a better grouped-action WES⁺[GitHub](https://github.com/WukLab/wuklab_sysml/blob/c99af641fbb403cb61df1ce74181bf9b90f6cda7/content/posts/oshuman.md#L34-L42)). The Executor uses the high-level plan as guidance – for instance, if the plan says “Step 2: compress the image in GIMP”, the Executor will focus on actions within GIMP rather than deviating. It also has access to a short history (last few actions/observations) to avoid immediate repetition and to know what sub-goal is completed. The Step Executor runs in a loop: observe -> decide -> act -> observe, until the task is done or fails.
- **Vision-Grounding Module (Grounder):** This module handles translation between abstract action targets and concrete GUI coordinates. It ensures **precision in clicking/typing**, which is critical for a high success rate (mis-clicks lead to extra corrective steps). The Grounder can operate in two modes:
  - *SoM tag mode:* When using SoM observations (tagged screenshots), the Executor’s output might refer to an element by its tag ID (e.g. “A3”). The Grounder maintains a mapping of tag IDs to actual coordinates (provided by the environment or computed via the accessibility info). For example, if “A3” corresponds to a button with bounding box (x=100,y=200,w=50,h=20), the Grounder may choose the center (125,210) as the click coordinate. It then formats the final action as required (e.g. `{"action": "LEFT_CLICK", "target": [125, 210]}`) before sending to `DesktopEnv.step()`.
  - *Semantic search mode:* If an output refers to an element by description (or if we weren’t using tags), the Grounder could use the accessibility tree or an OCR text search to find the intended element’s location. For example, if the model said “click the **Submit** button”, the Grounder can search the a11y tree for a node with name or text “Submit”, then retrieve its coordinates. This mode is a backup for cases where the model doesn’t give a tag or exact coordinate. In our design, we prioritize the SoM approach to let the model explicitly specify targets (reducing ambiguity).
  - The Grounder is essentially a lightweight **coordinate resolver**. It is not a learned neural module but a deterministic utility that uses the data in the observation to map references to coordinates. This separation of concerns lets the language model focus on *what* to click, and the Grounder figures out *where exactly* to click. This improves reliability, as the Grounder can e.g. adjust coordinates to avoid off by few pixels errors. Precise GUI grounding addresses one weakness of pure-LM agents, which sometimes click wrong locations due to limited image resolution or coordinate estimation errors.
- **Memory (State Tracker):** Our agent maintains a memory of important state across steps:
  - **Task Plan State:** After the Planner produces an initial plan, it’s stored. The agent can mark sub-goals as completed as it goes. For instance, if plan step 1 was “Open Chrome to URL” and that’s done, we mark it done and the next target is step 2. This can be simply stored in the agent object (e.g. an index of current plan step, or a list of booleans for done steps). The plan (or the next sub-goal) will be fed into the Executor’s prompt each step to keep it focused.
  - **Interaction History:** Instead of feeding the *entire* dialogue or all past observations at each step (which S2 did, incurring quadratic context growth[GitHub](https://github.com/WukLab/wuklab_sysml/blob/c99af641fbb403cb61df1ce74181bf9b90f6cda7/content/posts/oshuman.md#L26-L32)), we use a **truncated history** or summary. The agent might store the last few actions and outcomes (for example, “Clicked ‘Download’ button -> dialog opened” as a short fact). This helps for local context (what just happened), without sending a huge transcript to the model every time. We avoid long recursion of the full observation-action sequence in the prompt. If needed, we can maintain a *compressed memory* (like notes about which subtasks are done or any error messages seen). Qwen-3 8B has a limited context window, so this selective memory is vital.
  - **Environment State Memory:** Some tasks involve data that must be remembered (like a code snippet the agent copied, or a filename). The agent can store such information in variables (outside the model) when encountered – or as part of the plan state. For example, if the instruction says “save the file with a unique name,” the agent might generate that name and keep it in memory to use later.
  - In essence, this Memory component ensures the agent doesn’t lose track of the plan or repeat past mistakes. It’s simpler than a learning memory or vector database – mostly internal state and maybe a few heuristics (like detecting loops).
- **Optional Reflection Module:** If the agent executes many steps with no success, a **Reflection** can be triggered (by the Manager). This would pause normal execution and call the Qwen model in a different mode: asking it to analyze what’s gone wrong and suggest a correction. For example, if after 40 steps the goal isn’t reached, the Reflection prompt might include: *“You have tried steps that didn’t work. What could be a new approach or what did we miss?”*. The model might then output a revised plan or identify an overlooked GUI element (*“Perhaps the ‘Settings’ menu needs to be opened first”*). The Planner can incorporate this into a new plan, or directly instruct the Executor on a new subgoal. We include Reflection as an option because sometimes LLM agents get stuck in loops – a well-timed self-critique can break the loop. However, we design it to be used sparingly, because it’s effectively an extra planning step (which, if overused, hurts efficiency). In a robust agent, Reflection might only occur when the agent is e.g. 5 steps away from the max steps limit or has been idle (e.g. clicking around the same screen) for a while. If included, this module improves success chances at the cost of some efficiency; if excluded, the agent is simpler and faster but risks not recovering from errors. For Qwen-3 8B (a smaller model), a reflection step might help overcome its limited reasoning capacity on complex tasks, so it’s a worthwhile trade-off in difficult scenarios.

**Control Flow & Frequency:** The overall architecture operates in phases:



1. **Initialization:** On `env.reset(task)`, the agent’s Manager module reads the task instruction and produces an initial high-level plan (using one LLM call). The agent’s internal state is set (plan, step counter = 0, etc.).
2. **Main Loop:** For each step:
   - The environment provides an observation (screenshot + maybe structured data). The Executor formulates a prompt with this observation, the current plan context, and recent history. Qwen is called once to decide the next action or small action sequence.
   - The raw model output is parsed (JSON decoded) into a proposed action or actions. The Grounder then converts any abstract references (marks, element names) into concrete coordinates or key codes.
   - The actions are executed in the environment via `env.step()`. Each executed primitive yields a new state; if multiple actions were issued together, they are executed sequentially without intermediate reasoning (unless an unexpected change occurs that the agent should have awaited – we assume grouped actions are chosen such that they’re safe to do consecutively).
   - The agent increments the step count and updates its memory (log what was done, update plan progress if a subgoal completed).
   - If the model output was a special action `DONE` or `FAIL`, the loop breaks.
   - Otherwise, loop continues with the new observation.
3. **Reflection (if triggered):** If the loop is nearing max_steps or the agent is clearly off-track, the Manager can invoke a reflection: call the LLM with a special prompt (including a summary of attempts so far) to get a revised plan or hint. The plan is updated accordingly, and the main loop resumes with the new guidance.
4. **Termination:** On `DONE`, the environment’s evaluator runs to confirm success. On `FAIL` or exhausting max steps, the attempt ends as failure. The agent can log the outcome for learning (if we implement learning from experience).

This architecture is **modular** but uses the *same Qwen-3 VL model for all intelligent decisions* (planning, step decisions, reflection). We simply craft different prompts for different phases. This keeps the system lightweight (we’re not running multiple heavy models concurrently). Each module’s logic (Grounder, memory updates, etc.) is implemented in code around the LLM.

 

**Efficiency Considerations:** Compared to a naive “ask LLM every step with entire history” (like Agent S2 did[GitHub](https://github.com/WukLab/wuklab_sysml/blob/c99af641fbb403cb61df1ce74181bf9b90f6cda7/content/posts/oshuman.md#L26-L32)), our design reduces token usage and redundant reasoning by:



- Doing big-picture planning once (not at every step).
- Feeding only recent and relevant context to the LLM for decisions (not the full trajectory).
- Grouping actions when possible to cut down the number of steps (and thus LLM calls).
- Only invoking reflection (which is essentially an expensive re-planning) when absolutely needed, rather than having the model “reflect” every single turn.
  Each of these is aimed at improving the Weighted Efficiency Score on OSWorld-Human by trimming unnecessary steps/calls while maintaining success.

**Capabilities Mapping:** To tie back to needed abilities:



- *Vision/Text understanding:* handled by Qwen-VL on each observation.
- *Grounding:* handled by the Grounder with SoM tags and a11y info.
- *Planning:* handled by the Planner phase (Qwen prompt) and aided by the maintained plan context.
- *Reflection:* optional Qwen prompt when stuck.
- *Memory:* maintained by the agent code (limited context to Qwen).
- *Action abstraction:* achieved via allowing multi-action outputs and via the high-level plan guiding sequential actions.
- *Robustness:* The structured output and grounder reduce execution errors, and the reflection provides a safety net for stuck scenarios.

Next, we detail the prompt designs for each of these LLM interactions and then the code structure.



## 提示词（prompt）设计

We design **highly structured English prompts** to reliably guide the Qwen-3 8B model. Each prompt has specific roles:



### 1. 主 System Prompt (Agent Role Definition)

This system message establishes the agent’s identity, objectives, and output format. It remains constant throughout the session to enforce consistency. We clearly define the OSWorld context, available actions (the Computer_13 space), and the required JSON output schema.

 

**System Prompt Text:**



```
You are an intelligent desktop automation agent operating in a real computer environment (OSWorld). 
Your goal is to complete the user's task on the computer **as efficiently as possible**, using the fewest steps. 
You have a limited set of actions you can perform, and you MUST strictly output your actions in a structured JSON format (and nothing else).

**Environment:** You interact with a virtual Ubuntu desktop with various applications (e.g. browser, editor, email client). You receive visual observations (screenshots of the screen, possibly with certain UI elements labeled with tags like "A1", "B2", etc.) and sometimes additional UI information. The user’s instruction describes the goal to achieve (it can span multiple apps and steps).

**Available Actions (Computer_13):** You cannot execute arbitrary code; you can only output actions from this allowed list, with required parameters:
- `MOVE_CURSOR` – Move the mouse cursor to a coordinate. Parameters: `target` (the coordinates or UI element to move to).
- `LEFT_CLICK` – Click the left mouse button. Parameters: `target` (coordinates or UI element).
- `RIGHT_CLICK` – Right-click the mouse. Parameters: `target`.
- `DOUBLE_CLICK` – Double-click the left mouse button. Parameters: `target`.
- `DRAG_AND_DROP` – Click and drag from one point to another. Parameters: `source` (start coords/element), `target` (end coords/element).
- `SCROLL_UP` / `SCROLL_DOWN` – Scroll the mouse wheel up or down. Parameters: optionally `amount` (default some units if not provided).
- `TYPE` – Type text input on the keyboard. Parameters: `text` (the string to type). *(Ensure the target field is focused by a click first.)*
- `PRESS_KEY` – Press a single special key. Parameters: `key` (e.g. "Enter", "Escape", "Backspace", "ArrowUp", etc.).
- `HOTKEY` – Press a combination of keys together. Parameters: `keys` (an array of keys, e.g. ["Ctrl","S"] for save).
- `WAIT` – Wait for a short moment (to let the system load something). *No additional parameters.* 
- `DONE` – Declare that the task is completed successfully. *No additional parameters.* 
- `FAIL` – Declare that you cannot finish the task. *No additional parameters.*

Every action that involves a screen location (move or click, drag, etc.) should be grounded to the current observation:
  - If the observation image has tagged UI elements (like "A3", "B1" labels on components), use those tags to specify targets. Example: to click item labeled "A3", output: `"action": "LEFT_CLICK", "target": {"type": "mark", "id": "A3"}`. The environment will resolve the "A3" to the exact coordinates.
  - If no tag is available for the desired element, you may use absolute pixel coordinates: `"target": {"type": "coordinate", "x": 123, "y": 456}`. Only use coordinates if necessary – prefer marks for precision.
  - Do NOT guess random coordinates. Only click coordinates that correspond to something in the UI you observed.
  
**Output Format:** You must output a **JSON object** enclosed in triple backquotes, with the following structure:
```json
{
  "thought": "<brief reasoning here>",
  "plan": "<current high-level plan or subgoal context>",
  "actions": [
    {...}, 
    {...}
  ]
}
```

- `"thought"`: a short (1-2 sentences) explanation of why you chose these actions, or what you aim to do. Think of it as your internal reasoning, but keep it concise and relevant.
- `"plan"`: your current plan or the next sub-step you are addressing. This helps track progress. You should update this if your plan changes or as steps are completed. (For example, you can list remaining subgoals or indicate completion of parts of the task.)
- `"actions"`: an array of one or more action objects to execute now. Typically 1-3 actions that can be done in the current screen without needing a new observation. Each action object must have an `"action"` field (one of the allowed actions above), and appropriate parameters:
  - If the action uses a target, provide either a `{"type": "mark", "id": "<TagID>"}` or `{"type": "coordinate", "x": ..., "y": ...}`.
  - For `TYPE`, include `"text": "<string>"`.
  - For `PRESS_KEY` or `HOTKEY`, include the `"key"` or `"keys"` fields.
  - For `WAIT`, `DONE`, `FAIL`, no additional fields are needed (you can put an empty object or just `"action":"WAIT"`).

Your JSON **must** conform to this schema exactly. Do not include any explanatory text outside the JSON. Do not deviate from the allowed actions or format.

 

**Goals and Efficiency:** Always aim to complete the task in as few steps as possible. Avoid unnecessary actions or redundant observations. If you believe you have accomplished the task’s goal, use `DONE`. If you are truly stuck or the instruction cannot be completed, use `FAIL` (but only as a last resort). Use `WAIT` if you expect the system needs a moment (e.g., waiting for a page to load) instead of clicking around impatiently.

 

You are a reliable, efficient agent. Now, let’s begin.



```
*(The system prompt above defines the agent’s role and formatting. It lists all the **Computer_13** actions and how to specify targets:contentReference[oaicite:52]{index=52}:contentReference[oaicite:53]{index=53}, and it enforces the JSON schema. It also underscores efficiency and the use of marks for GUI grounding.)*

### 2. 单步决策 Prompt (User Prompt Template per Step)

Each step, we feed the model a **user message** describing the current state and asking for the next action. We populate it with relevant context: the task, our plan, progress, and the latest observation. For Qwen-VL, this includes an image attachment for the screenshot.

**User Prompt Template (variables in braces to be filled at runtime):**
```

User Task: "{instruction}"

 

Current Plan: "{current_plan_status}"
Step: {step_idx}/{max_steps}
Recent Actions: {recent_actions_summary}

 

Observation:



- Screenshot: (attached below)
  {optional_additional_info}

Given the above, what is the **next action or actions** you will take?
Remember: respond with a JSON with your thought, updated plan, and 1-3 actions.



```
Let’s break down how to fill this:
- **User Task:** We remind the agent of the original instruction each time, to keep it focused on the end goal. This is especially important for long tasks so the model doesn’t lose context of what the user ultimately wants.
- **Current Plan:** We insert a concise representation of the agent’s understanding of the plan or subgoal at this point. For example, initially this could be the list of planned sub-tasks. As steps progress, it could be updated like: *“Plan: 1) Do X (done), 2) Do Y (in progress), 3) Do Z (remaining)”*. If a reflection updated the plan, we show the new plan here. This keeps the model aware of what part of the task we are on. (This acts as a form of short-term memory and guidance).
- **Step:** Indicates which step number we’re on and the maximum allowed. E.g. “Step: 5/50”. This subtly pressures the agent to be efficient. Seeing the step count rise might encourage it to wrap up sooner (to avoid hitting the limit). It also gives awareness for reflection triggers (if step is high).
- **Recent Actions:** A brief summary of the last 1-2 actions and results, if relevant. For example: *“Recent Actions: Clicked ‘Download’ button (dialog opened)”* or *“Typed login, pressed Enter (login failed error shown)”*. We won’t list a huge history – just the immediate context or any noteworthy outcome (especially if the last action led to an error or new window). This helps the model adjust its strategy appropriately. If nothing notable happened or it’s the first step, this can be omitted.
- **Observation:** This section describes what the agent currently perceives.
  - We will **attach the screenshot image** here. In an actual implementation with Qwen-VL, we would attach the image in the message payload. For this template, we just note it’s attached.
  - If using SoM, the screenshot image would have tags visible. We may also provide an **additional info** line listing the SoM tags and their associated element names/text (if that information is available). For example, we might include lines like:
    ```
    Visible UI elements: A1 (Chrome icon), A2 (“File” menu), A3 (“Open” button), B1 (text field), ...
    ```
    This text helps the model map tags to actual interface elements (especially if the model’s vision is not perfectly reading the tiny text on the screenshot). However, to save tokens, we might only list a few relevant tags or none at all if the screenshot is clear. We include `{optional_additional_info}` as a placeholder for any text-based observation data. If we were in combined mode (screenshot + a11y), this would contain the linearized a11y tree info:contentReference[oaicite:54]{index=54}:contentReference[oaicite:55]{index=55}. In SoM mode, it could be a list of tag descriptions or could be left empty to let the image speak for itself. 
- **Prompt question:** We end by explicitly asking for the next action(s) and reminding the model to use the JSON format. This is crucial to trigger the model’s formatting behavior. The phrasing *“what is the next action or actions”* hints that it can propose multiple actions if appropriate.

**Example filled-in user prompt (for a specific step):**

Suppose the task is *“Send an email to Bob with the subject ‘Report’ and attachment ‘report.pdf’.”* The agent’s current plan (from initial planning) is:
1. Open email client.
2. Compose a new email to Bob with subject and attach file.
3. Send the email.

Now say we are at Step 3/50, having already opened the client (step 1 done) and clicked “New Email” (step 2 partially done). The observation is a screenshot of the compose window with fields for To, Subject, etc., labeled with tags A1, A2, etc.

The prompt might be:
```

User Task: "Send an email to Bob with the subject 'Report' and attachment 'report.pdf'."

 

Current Plan: "1) Open Thunderbird (done), 2) Compose email to Bob (in progress), 3) Attach file and send (pending)"
Step: 3/50
Recent Actions: Clicked "New Message" (compose window opened)

 

Observation:



- Screenshot: (attached below)
  Visible UI elements: A1 (To: field), A2 (Subject: field), A3 (Attach button), A4 (Send button), B1 ("report.pdf" file icon on Desktop)

Given the above, what is the next action or actions you will take?
Remember: respond with a JSON with your thought, updated plan, and 1-3 actions.



```
In this example, the agent can see tags A1–A4 for the email fields/buttons, and maybe the Desktop with the file (tag B1). It knows from plan we need to fill the fields, attach file, then send. The prompt has set all this context.

### 3. Reflection Prompt (Optional)

When triggered (e.g., the agent has taken many steps with little progress, or we detect a loop or error condition), we switch to a reflection mode prompt. The goal here is to have the model step back, analyze the situation, and suggest a corrected approach or updated plan, rather than continuing blindly.

The Reflection prompt can reuse the System role definition (the agent’s identity and rules remain the same), but the user message will be different. We’ll ask the model to *ignore the normal action output format* for a moment and just produce a revised plan or insight. (Alternatively, we could still ask for a JSON with a “plan” field and no actions, but it might be simpler to get a textual plan and then feed that back into the main prompt sequence.)

**Reflection User Prompt Template:**
```

*** REFLECTION Mode ***
The agent has executed {step_idx} steps out of {max_steps} but has not achieved the goal yet. It appears to be off track or stuck.

 

Summary of the situation:



- Task: "{instruction}"
- Plan so far: {current_plan_status}
- Actions taken: {summary_of_actions_taken}
- Current obstacle: {describe_problem_or_stuck_state}

Analyze what went wrong or what is missing. Devise a revised plan to complete the task, or a new approach.
Focus on efficiency: how can we finish in the few remaining steps?

 

Output a brief reflection on the mistakes so far, then list a revised plan of action. Do NOT output any JSON action now, just a reflection and an updated plan.



```
In this prompt:
- We clearly label it as REFLECTION mode to differentiate from normal operation.
- We give a bullet-point summary:
  - The task (reminder of goal),
  - The plan so far (and what’s done vs not done),
  - Actions taken (maybe compressed list of key actions),
  - The current obstacle or reason we think we’re stuck (e.g. *“We keep clicking login but it fails – maybe the password is wrong”* or *“We have downloaded the file but can’t find it to attach”*).
- We explicitly instruct the model to analyze and give a *revised plan* rather than continuing with the old approach. Also, we caution not to output JSON actions here.
- Essentially, we’re asking for something like: *“I realize I was looking in the wrong menu. I should instead do X. Revised Plan: 1)… 2)… etc.”*

**Expected Reflection Output:** The model might output something like:

“**Reflection:** I attempted to find the “Settings” in the File menu repeatedly, which was a mistake. The application’s settings are under the Edit menu, which I overlooked. I also wasted steps clicking the wrong buttons. 

**Revised Plan:** 1) Open the Edit menu to access Preferences. 2) Change the configuration as needed. 3) Save and exit settings. 4) Continue with task (the remaining steps).”

This would come as a plain text (or we could enclose it in a JSON with a special field if we want to parse it). We will parse or extract the Revised Plan from this output.

After reflection, we integrate the new plan: update the agent’s `current_plan_status` and perhaps reset some internal counters if needed. Then we resume normal execution prompting, with the new plan included in the System/User prompts going forward.

*(Note: In implementation, the reflection might be handled by calling the model with a modified system instruction that still allows some free-form reasoning. Given Qwen-3 8B’s limitations, we might also simplify the reflection to just asking “Summarize what’s done and what to do next” rather than complex analysis. But the above is the ideal design.)*

### JSON Output Schema & Examples

As defined in the system prompt, every normal step response must be a JSON object with fields: `thought`, `plan`, `actions`. We enforce that it’s the sole content in a markdown code block. Here are a couple of example outputs the agent might produce:

- **Example 1: Single action step (with SoM tag):**

  Suppose the agent needs to click the “Compose” button (tagged A5) in an email client to start a new email.

  ```json
  {
    "thought": "I need to open a new email compose window.",
    "plan": "Step 2/3: Open compose window (ongoing), then attach file, then send email.",
    "actions": [
      {
        "action": "LEFT_CLICK",
        "target": { "type": "mark", "id": "A5" }
      }
    ]
  }
```

- *thought:* The agent succinctly states why it’s doing this (to open compose window).

- *plan:* It shows the current segment of the plan (it’s in step 2 out of 3 total plan steps, and currently “ongoing”).

- *actions:* A single left-click on element A5 (the Compose button). The agent used the mark “A5” rather than a raw coordinate, which the Grounder will map to the actual position[GitHub](https://github.com/SunzeY/SEAgent/blob/c8887f157352494953b3317047929cf81465defa/OSWorld/mm_agents/agent.py#L120-L128).

- **Example 2: Grouped actions step (two actions):**

   

  The agent has a file browser open and wants to rename a file “report.txt” to “report.pdf”. It knows it can click the filename (tag B3), then press F2 (rename key), then type the new name. Perhaps it groups clicking the file and pressing F2 in one go (assuming the UI will enter rename mode on F2 without needing a new screenshot).

  ```
  {
    "thought": "To rename the file, I will select it and initiate rename.",
    "plan": "Renaming the file before attaching it (remaining steps in plan).",
    "actions": [
      {
        "action": "LEFT_CLICK",
        "target": { "type": "mark", "id": "B3" }
      },
      {
        "action": "PRESS_KEY",
        "key": "F2"
      }
    ]
  }
  ```

  Here, two actions are listed: one to select the file (click it), second to press F2 to start renaming. The thought explains the combined intent. After execution, likely the environment will highlight the filename for editing. The agent would then in the next step type the new name (that could also possibly be grouped here, but it might wait to see the UI response).

- **Example 3: Including a typing action:**

   

  If continuing the above scenario, next step might be:

  ```
  {
    "thought": "Now typing the new filename and confirming.",
    "plan": "File renamed; next attach it to email (plan updated).",
    "actions": [
      {
        "action": "TYPE",
        "text": "report.pdf"
      },
      {
        "action": "PRESS_KEY",
        "key": "Enter"
      }
    ]
  }
  ```

  This outputs a TYPE followed by pressing Enter (to finalize the rename). The target for typing isn’t specified because after F2, the OS focuses the filename input. (In our schema, we didn’t require a target for TYPE if an input field is already focused by a prior click.)

- **Example 4: Finishing up (DONE action):**

   

  After sending the email successfully:

  ```
  {
    "thought": "The email has been sent successfully. Task completed.",
    "plan": "All steps finished.",
    "actions": [
      { "action": "DONE" }
    ]
  }
  ```

  This indicates the agent believes the goal is accomplished and signals completion. The environment will run the evaluator to verify success[GitHub](https://github.com/tylerelyt/test_bed/blob/6448e3f7d1bbdefcb4354e4ab79eec9c175bf941/docs/GUI_AGENT_GUIDE.md#L164-L169).

- **Example 5: In case of failure (FAIL action):**

   

  If something went irrecoverably wrong (e.g., no internet to send email):

  ```
  {
    "thought": "I have no network connection and cannot proceed further.",
    "plan": "Unable to complete the task due to external issue.",
    "actions": [
      { "action": "FAIL" }
    ]
  }
  ```

  This would cause the run to end with failure, and WES⁻ would be calculated based on steps used[mlsys.wuklab.io](https://mlsys.wuklab.io/posts/oshuman/#:~:text=Failed Task%3A %24r_t %3D 0%24).

All these examples strictly follow the JSON format specified. They demonstrate how the agent interleaves reasoning (`thought`), planning context (`plan`), and action commands. By providing a consistent schema and examples, we aim to maximize the chance Qwen-3 8B adheres to the format and produces valid actions for the environment to execute.



## Agent 代码骨架

Below is a pseudocode/Python-style outline for the agent implementation, integrating the above modules and prompts. This `QwenOSWorldAgent` class can interface with the OSWorld `DesktopEnv`. Note that actual image handling and model API calls are simplified for clarity:



```
class QwenOSWorldAgent:
    def __init__(self, model, observation_type="som", action_space="computer_13", max_steps=50):
        """
        Initialize the agent.
        :param model: A handle to the Qwen-3 VL 8B model (e.g., an API client or pipeline).
        :param observation_type: Type of observations used (e.g., "som", "screenshot", etc.).
        :param action_space: Type of action space ("computer_13" here).
        :param max_steps: Max steps allowed for a task (for reference in prompts).
        """
        self.model = model  # This could be an object with a generate/chat method.
        self.observation_type = observation_type
        self.action_space = action_space
        self.max_steps = max_steps

        # Internal state
        self.plan = None
        self.current_step = 0
        self.history = []       # to store recent (obs, action, result) tuples if needed
        self.plan_history = []  # store plan or reflection outputs if needed for debugging

        # Compose the system prompt once
        self.system_message = SYSTEM_PROMPT  # from the prompt design above (string)
    
    def reset(self, task_instruction):
        """
        Start a new task. Clears history and obtains an initial high-level plan.
        :param task_instruction: The natural language task description.
        """
        self.current_step = 0
        self.history = []
        # Optionally get initial observation outside (DesktopEnv.reset gives it)
        # For planning, we might not need the image, just instruction.
        self.plan = None

        # PLAN: Use the model to generate a high-level plan for the task
        planning_prompt = (f"You are to plan the task: {task_instruction}\n"
                            "Break it down into a sequence of high-level steps.")
        # We send a one-off prompt to the model (could be as system+user or just user) to get plan.
        plan_response = self.model.generate(planning_prompt, max_tokens=200)
        # Parse the plan from the model's response (which might be a numbered list of steps).
        self.plan = self._parse_plan(plan_response)
        self.plan_history.append(self.plan)
        # Log the plan
        print(f"Initial plan: {self.plan}")
        # No prediction yet – waiting for the first observation from env.reset outside.
    
    def predict(self, observation):
        """
        Given the current observation, decide the next action(s).
        :param observation: The observation dict from the environment (may include screenshot etc.).
        :return: A list of action commands (dictionaries) for the environment.
        """
        self.current_step += 1

        # 1. Construct the message list for the model (system + user with context)
        messages = []
        # System role
        messages.append({"role": "system", "content": self.system_message})

        # User role with the formatted prompt
        user_content = self._build_user_prompt(observation)
        messages.append({"role": "user", "content": user_content})

        # 2. Call the Qwen model to get a response
        response = self.model.chat(messages)  # assuming .chat returns the assistant message text
        # Alternatively, if using an API: response = openai.ChatCompletion.create(...)

        # 3. Parse the JSON from the model's response
        action_plan = self._parse_model_output(response)
        if isinstance(action_plan, str):
            # If parsing failed or got a string error like "Failed to parse JSON"
            print(f"Error parsing model output: {action_plan}")
            # We could decide to fail or just skip this step.
            return []

        thought = action_plan.get("thought", "")
        updated_plan = action_plan.get("plan", None)
        actions = action_plan.get("actions", [])

        # 4. Update internal plan if the model adjusted it
        if updated_plan and updated_plan != "":
            self.plan = updated_plan  # This could be a string description; in a more structured approach we’d parse if needed.
        
        # 5. Ground any actions with marks to coordinates
        concrete_actions = []
        for act in actions:
            if act.get("action") in ["DONE", "FAIL", "WAIT"]:
                # Special actions pass through
                concrete_actions.append({ "action": act["action"] })
            else:
                target = act.get("target")
                # If target is specified by mark or coordinate, resolve it:
                if target:
                    if target.get("type") == "mark":
                        mark_id = target.get("id")
                        coord = self._resolve_mark_to_coord(mark_id, observation)
                        if coord:
                            act_concrete = act.copy()
                            act_concrete.pop("target", None)
                            act_concrete["coordinate"] = coord
                            concrete_actions.append(act_concrete)
                        else:
                            print(f"Warning: could not resolve mark {mark_id} to coordinate.")
                            # If unresolved, skip or fail this action
                    elif target.get("type") == "coordinate":
                        # Already given as explicit coordinates
                        x = target.get("x"); y = target.get("y")
                        act_concrete = act.copy()
                        act_concrete["coordinate"] = [x, y]
                        act_concrete.pop("target", None)
                        concrete_actions.append(act_concrete)
                else:
                    # Actions like TYPE or HOTKEY with no screen target
                    concrete_actions.append(act)
        
        # 6. (Optional) If model signaled reflection or a new plan in a special way, handle it.
        # In our design, reflection would be handled outside of this method by triggering a separate call.

        # 7. Save to history (for potential context or debugging)
        self.history.append({
            "observation": observation,
            "thought": thought,
            "actions": concrete_actions
        })
        # Possibly also save the model's raw output text if needed.

        return concrete_actions

    # --- Helper methods ---

    def _build_user_prompt(self, observation):
        """Format the user prompt string with current context and observation."""
        # Use the template described above.
        task = "<unknown task>"
        current_plan_str = ""
        if isinstance(self.plan, list):
            # If plan stored as list of steps, highlight done vs not done
            # For simplicity, join them or mark current step.
            plan_lines = []
            for i, step_descr in enumerate(self.plan, start=1):
                if i < self.current_step_plan_index:
                    plan_lines.append(f"{i}) {step_descr} (done)")
                elif i == self.current_step_plan_index:
                    plan_lines.append(f"{i}) {step_descr} (current)")
                else:
                    plan_lines.append(f"{i}) {step_descr}")
            current_plan_str = " -> ".join(plan_lines)
        elif self.plan:
            current_plan_str = str(self.plan)
        else:
            current_plan_str = "No plan."

        step_status = f"{self.current_step}/{self.max_steps}"
        recent_summary = ""
        if self.history:
            # Summarize last action and result for context
            last = self.history[-1]
            # (We would need a function to interpret last['observation'] difference or environment feedback to summarize result)
            # As a simple approach, if last action had a certain known effect or if env provided an 'info':
            # Suppose observation contains info like 'error' or the title of window.
            # We'll skip detailed implementation here.
            recent_summary = self._summarize_last_action(last)
        
        # Observation details:
        obs_text = ""
        # If we have an image, we plan to attach it separately, but Qwen may need a placeholder:
        # e.g., we might provide something like "<Screenshot Image>" or just ensure the image is in the messages.
        obs_text += "- Screenshot: (see attached image)\n"
        # Add any additional textual info from observation:
        if 'a11y_tree' in observation and observation['a11y_tree']:
            # Include a truncated or formatted portion of the accessibility text if needed
            a11y_info = observation['a11y_tree']
            obs_text += f"Accessible UI info:\n{a11y_info}\n"
        if 'som_elements' in observation:
            # A list of tags and descriptions
            elements = observation['som_elements']  # e.g., [ {"id":"A1", "name":"File menu"}, ... ]
            elem_lines = [f"{el['id']}: {el['name']}" for el in elements]
            obs_text += "Visible UI elements: " + ", ".join(elem_lines) + "\n"

        # Compose everything
        prompt = (f'User Task: "{task}"\n'
                  f'Current Plan: "{current_plan_str}"\n'
                  f'Step: {step_status}\n')
        if recent_summary:
            prompt += f'Recent Actions: {recent_summary}\n'
        prompt += f'\nObservation:\n{obs_text}\n'
        prompt += "Given the above, what is the next action or actions you will take?"
        prompt += "\n(Remember to reply in JSON format.)"
        return prompt

    def _parse_model_output(self, model_response):
        """Extract JSON from the model's response text."""
        # Assume model_response is a string of the assistant's answer.
        import json, re
        text = model_response.strip()
        # Find JSON content within triple backticks if present
        match = re.search(r"```json(.*?)```", text, re.DOTALL)
        if not match:
            match = re.search(r"```(.*?)```", text, re.DOTALL)
        try:
            if match:
                json_str = match.group(1)
            else:
                # If no code fences, assume the whole response is JSON
                json_str = text
            result = json.loads(json_str)
            return result
        except json.JSONDecodeError as e:
            return f"Failed to parse JSON: {e}"

    def _resolve_mark_to_coord(self, mark_id, observation):
        """Look up the coordinates for a given SoM mark id from the observation."""
        # Assuming observation might contain a mapping of mark IDs to coordinates.
        if 'marks' in observation:
            # e.g., observation['marks'] could be {"A1": [x,y,w,h], ...}
            if mark_id in observation['marks']:
                bbox = observation['marks'][mark_id]  # [x, y, w, h]
                # Return center of the bounding box
                x, y, w, h = bbox
                return [x + w//2, y + h//2]
        if 'som_elements' in observation:
            for el in observation['som_elements']:
                if el.get('id') == mark_id:
                    # If element has exact coord (maybe stored)
                    if 'center' in el:
                        return el['center']
                    elif 'bbox' in el:
                        bx, by, bw, bh = el['bbox']
                        return [bx + bw//2, by + bh//2]
        # If not found:
        return None

    def _parse_plan(self, plan_text):
        """Parse the high-level plan text into a structured form (list of steps or string)."""
        # Could split by line breaks or numbers.
        steps = []
        for line in plan_text.splitlines():
            line = line.strip("-•1234567890. ")  # remove list markers
            if line:
                steps.append(line)
        return steps if steps else plan_text

    def _summarize_last_action(self, last_entry):
        """Summarize the last action and its outcome for context (simple heuristic)."""
        # This could be complex; for now, just echo the last action.
        acts = last_entry.get("actions", [])
        if not acts:
            return ""
        descriptions = []
        for a in acts:
            act = a.get("action")
            if act in ["LEFT_CLICK", "RIGHT_CLICK", "DOUBLE_CLICK"]:
                target = a.get("target") or a.get("coordinate")
                if isinstance(target, dict) and target.get("type") == "mark":
                    desc = f'Clicked "{target["id"]}"'
                elif isinstance(target, list):
                    desc = f'Clicked at {target}'
                else:
                    desc = f'Clicked'
                if act == "RIGHT_CLICK": desc = "Right-" + desc
                if act == "DOUBLE_CLICK": desc = "Double-" + desc
                descriptions.append(desc)
            elif act == "TYPE":
                text = a.get("text", "")
                descriptions.append(f'Typed "{text}"')
            elif act == "PRESS_KEY":
                key = a.get("key", "")
                descriptions.append(f'Pressed {key}')
            elif act == "HOTKEY":
                keys = "+".join(a.get("keys", []))
                descriptions.append(f'Pressed {keys}')
            elif act == "WAIT":
                descriptions.append("Waited")
        # If we had an outcome from env (like an error dialog), ideally include it.
        # Without environment info, we'll keep it basic.
        return "; ".join(descriptions)
```

**Explanation:**



- The `QwenOSWorldAgent` holds the model and configuration. On `reset`, it clears state and uses the model to generate an initial plan from the instruction (via a simple prompt). We parse that into a list of steps for internal use.

- The `predict` method is the core. It constructs the messages: the system prompt is constant, then the user prompt via `_build_user_prompt(observation)`. That function uses our template, including task, plan, step count, recent actions, and the observation. It attaches the screenshot image as needed when sending to the model (in the pseudocode, we just mention it; in reality, with Qwen’s API we might supply the image bytes or a path).

- We then call `self.model.chat(messages)` – this assumes the model interface can take a list of messages (like OpenAI ChatCompletion). Qwen-3 VL might have a similar interface where we provide the system and user content (and image). We’d adjust this call according to the actual API (for example, some interfaces require the image to be provided as a separate parameter or as a special token).

- The raw response is parsed by `_parse_model_output` which looks for a JSON blob in the assistant’s reply. We handle cases where the model might include markdown fences. We attempt `json.loads` to get a Python dict. If it fails, we return an error string.

- We then extract `thought`, `plan`, `actions`. If the model provided an updated plan (as a string), we update `self.plan`. (In a more advanced setup, we might reconcile this with our structured plan list or keep both).

- Next, we “ground” the actions: for each action, if it has a mark target, we resolve it to coordinates using the observation’s data (the observation should contain either a `marks` dict or `som_elements` list with positions). Coordinates are chosen, for example as the center of the element’s bounding box. This yields a concrete action dict that the environment can execute. We leave special actions as is.

- We then append the result to history (including the thought for possible debugging or reflection triggers).

- Finally, we return the list of `concrete_actions`. If multiple, the environment (or our wrapper) can execute them in sequence. Alternatively, we might choose to execute them one by one inside `predict` and only return after the last, but returning the batch allows the outer loop to handle execution.

- Other helper methods:

  - `_build_user_prompt` uses the template to assemble the string. It attaches the image and any text info (like a truncated a11y tree or list of visible elements). We make sure to include recent context and plan.
  - `_parse_model_output` and `_parse_plan` handle string parsing.
  - `_resolve_mark_to_coord` is the Grounder’s core: given a mark ID and observation data, find the coordinate (we assume observation might carry a dictionary of mark IDs to bounding boxes). This depends on how OSWorld provides the SoM info – we might have to adapt it. Here we assume either `observation["marks"]` is a dict of `id: [x,y,w,h]` or `observation["som_elements"]` is a list of element info. We return an [x,y] pair for the coordinate.
  - `_summarize_last_action` (very rudimentary here) tries to convert the last taken actions into a human-readable summary for the prompt. In practice, we might enhance this with actual results (like if last observation shows an error message, include that). This part can be complex, but even a simple summary of “Clicked X” helps the model not repeat that immediately.

- The agent would be used like:

  ```
  env = DesktopEnv(...)  # OSWorld environment
  agent = QwenOSWorldAgent(model=qwen_model)
  task = task_json["instruction"]
  obs = env.reset(task_json)  # get initial observation
  agent.reset(task)  # initialize agent and get high-level plan
  for t in range(agent.max_steps):
      actions = agent.predict(obs)
      for act in actions:
          obs, reward, done, info = env.step(act)
          # If multiple actions were given, we loop. We break out if done in between.
          if done:
              break
      if done:
          break
  if done:
      print("Task done, success?" , True if reward>0 else False)
  else:
      print("Max steps reached, failing task.")
  ```

  This loop executes until the agent outputs DONE/FAIL or runs out of allowed steps. The agent’s prompts ensure it knows the step count and will ideally use DONE/FAIL appropriately.

Note: The actual integration with vLLM’s deployment of Qwen might require calling a local HTTP endpoint or pipeline with the image. For instance, using `model.predict(images=[...], texts=[...])`. The pseudocode assumes a `model.chat` or `model.generate` that can accept our constructed messages. In practice, one would adapt it to however vLLM exposes Qwen (possibly through an OpenAI-compatible API or a huggingface pipeline).



## 与 Agent-S / 基线 对比和优化建议

Let’s compare our proposed Qwen-3 8B agent with the OSWorld baseline (e.g., Agent S2) and the Agent-S paradigm (notably the latest S3 deployment), along key dimensions:



- **Model Usage & Quantity:** The baseline OSWorld agents often rely on a *single large LLM*, e.g., GPT-4 or Claude, to handle everything[github.com](https://github.com/WukLab/osworld-human#:~:text=UI,0.33). Agent S2, for instance, is a framework that can plugin different LLMs (the leaderboard shows S2 with “Gemini 2.5” and S2 with “Claude 3.7”)[github.com](https://github.com/WukLab/osworld-human#:~:text=UI,0.33). It generally used one model at a time for the main reasoning loop. Some versions augmented this with external tools (like an OCR or object detector) as preprocessing[GitHub](https://github.com/tylerelyt/test_bed/blob/6448e3f7d1bbdefcb4354e4ab79eec9c175bf941/docs/GUI_AGENT_GUIDE.md#L114-L123), but the heavy lifting is one model. Agent-S3 (the next-gen) might incorporate multiple specialized models – given *“Generalist-Specialist”* naming, possibly a larger planner and smaller executors per domain, or some learned vision module. Our Qwen-3 VL agent uses **one model (8B)** for both vision and language understanding. This is a much smaller model than GPT-4 (175B) or Claude 3.7 (likely 3.7× larger or so). The advantage is speed: Qwen-3 8B running locally on vLLM can be significantly faster per step, reducing wall-clock latency. The disadvantage is capability: it may not have the same reasoning depth or accuracy. We mitigate this with structured prompts and a plan to keep it focused. In terms of model count, our architecture doesn’t employ separate specialized models – everything (planning, executing, reflecting) is done by the single Qwen instance. This keeps integration simple (no model switching overhead), at the cost that Qwen must multitask. Agent-S3 could potentially use a larger model for planning and a smaller for execution to save time. If needed, our design could mimic that by using Qwen-3 for vision perception and a bigger LLM for tough planning, but that would add complexity. For now, simplicity (one model) is chosen due to resource constraints.
- **Grounding Ability & Precision:** The baseline and Agent S2 initially struggled with precise GUI grounding – GPT-4 would output coordinates that were sometimes slightly off, requiring multiple tries[GitHub](https://github.com/tylerelyt/test_bed/blob/6448e3f7d1bbdefcb4354e4ab79eec9c175bf941/docs/GUI_AGENT_GUIDE.md#L50-L58). To address this, OSWorld baseline prompts emphasized *not* using image-search functions and to guess coordinates carefully[GitHub](https://github.com/tylerelyt/test_bed/blob/6448e3f7d1bbdefcb4354e4ab79eec9c175bf941/docs/GUI_AGENT_GUIDE.md#L50-L58). Agent S2 with SoM (tagged screenshot) was introduced to improve grounding, but interestingly GPT-4V performed slightly worse with tags than with full a11y text[papers.nips.cc](https://papers.nips.cc/paper_files/paper/2024/file/5d413e48f84dc61244b6be550f1cd8f5-Paper-Datasets_and_Benchmarks_Track.pdf#:~:text=,a11y tree inputs%2C which). Possibly GPT-4V didn’t need the tags as much due to its powerful vision, whereas a smaller model might benefit more from tags. Our Qwen agent leans heavily on the **SoM approach**: we provide labeled UI elements and require the model to use those labels in its output. This should yield near pixel-perfect targeting – the Grounder maps tags to exact coordinates, removing ambiguity. Compared to baseline (which in code mode might output e.g. `pyautogui.click(105, 212)` directly[GitHub](https://github.com/tylerelyt/test_bed/blob/6448e3f7d1bbdefcb4354e4ab79eec9c175bf941/docs/GUI_AGENT_GUIDE.md#L54-L58)), our method ensures we click the correct element if the model picks the right tag. In terms of precision, this design is **more reliable**: no random coordinate guesses, and less risk of missing the small target (the Grounder can even enlarge click area or ensure center-of-button clicks). Agent-S3 likely also emphasizes improved grounding; possibly it uses an object detection model to identify clickable regions or a learned visual grounding model (there’s research on this)[openreview.net](https://openreview.net/forum?id=zg5is4GJ3R#:~:text=for,Table 8 of the). Our approach is a more heuristic one (tags + deterministic mapping) but effective. Future optimization here could include a dedicated lightweight vision model to verify the model’s chosen target (for instance, a classifier that checks if “A3” indeed corresponds to a “Submit” button by reading the pixels). Alternatively, training Qwen-3 on some GUI images with tags could enhance its understanding of the tag system. But even as-is, the structured output plus grounder should surpass the baseline’s raw coordinate accuracy.
- **Planning & Reflection Strategy:** Baseline Agent S2, as noted, did a form of chain-of-thought planning at every step (the system prompt encouraged reasoning and it likely output a thought before each action). It didn’t explicitly separate a one-time planner; instead, it interleaved planning into the step-by-step process. This led to repetitive re-evaluation of the entire history and goal, causing massive slow-downs as tasks grew long[GitHub](https://github.com/WukLab/wuklab_sysml/blob/c99af641fbb403cb61df1ce74181bf9b90f6cda7/content/posts/oshuman.md#L26-L32). Agent S2 also included a reflection mechanism (possibly when an attempt failed, it would try an alternate method – e.g., after hitting an error, it might reconsider). But this was still done with the same large model, adding to latency. Agent-S3 presumably addresses this by not carrying full history each time and possibly by using a hierarchical policy (plan at a high level once, then execute) – which is exactly what we implement. Our agent explicitly **splits planning and execution**. The plan is formed once and reused, which should drastically cut down on repeated computation. Also, by keeping the prompt lean (only recent context, plus the plan summary), we avoid quadratic context growth. We do allow reflection but as an out-of-band event, not every step. This approach should improve the Weighted Efficiency Scores:
  - Fewer LLM calls overall (one upfront for planning, then one per step, rather than potentially multiple per step if the baseline did reflection each time).
  - Shorter prompts per call (since we don’t append all previous observations beyond a certain small window).
    Both translate to speed. The risk is that the agent might not correct its plan if things go wrong, unless we catch it and do reflection. The baseline might organically adjust because it’s always re-thinking with full context (though at great expense). Our design might stick to a flawed plan longer. We mitigate that with the reflection trigger.
    In summary, our strategy is **plan once, act many**, versus baseline’s “plan a little at each step.” This should be far more efficient temporal-wise[GitHub](https://github.com/WukLab/wuklab_sysml/blob/c99af641fbb403cb61df1ce74181bf9b90f6cda7/content/posts/oshuman.md#L26-L32), and align with how humans operate (we don’t completely re-think the entire task after every single click). There’s a slight sacrifice in flexibility, but we gave ourselves an escape hatch via reflection.
    One more note: Multi-step action grouping is another planning aspect – our agent can output grouped actions. Baselines historically did one action per step (thus a one-to-one mapping of agent steps to environment steps). By sometimes doing 2-3 actions in a single reasoning step, we can directly cut down the *number* of LLM calls and environment interactions. For OSWorld-Human’s grouped-action metric, this is beneficial[GitHub](https://github.com/WukLab/wuklab_sysml/blob/c99af641fbb403cb61df1ce74181bf9b90f6cda7/content/posts/oshuman.md#L34-L42). We have to ensure the model is competent enough to decide when grouping is safe – which is why we mention grouping only “if the UI likely doesn’t change.” This behavior might emerge from examples or few-shot or system prompt hints. We explicitly encouraged grouping in the system prompt (“1-3 actions”) and in the user prompt. Testing and tweaking would be needed, but even partial success in grouping (like always grouping typing after a click into a text field) would improve efficiency.
- **Expected Performance (OSWorld and OSWorld-Human):**
  - On **success rate** (original OSWorld metric): Our agent uses a much smaller model than top competitors (GPT-4-based), so we expect a somewhat lower success rate on complex tasks due to limited reasoning or vision accuracy. However, Qwen-3 VL is still a strong model for its size and, with the structured approach, might surprise in being able to follow through many simpler tasks. The precise action targeting will prevent some failures (the baseline might fail a task simply by clicking wrong and messing up an app’s state; our agent should make fewer such mistakes). Also, having a plan might help it not forget steps, improving completion. If the tasks have moderate complexity, we anticipate a decent success rate, though likely not topping GPT-4V.
  - On **WES⁺ and WES⁻:** This is where our design shines. By reducing step count, we aim for a higher WES⁺. Even if success is slightly lower, a high efficiency can yield a better overall WES (since WES weighs efficiency into success). The grouping of actions directly reduces *tₐ* (agent steps) for a given *tₕ* (human steps), raising WES⁺. Also, our agent is programmed to call `FAIL` earlier if stuck. Baseline agents often run until 50 steps then fail, incurring WES⁻ of nearly -1. We can do better by recognizing when we’re lost at, say, 30/50 steps and calling FAIL there – yielding WES⁻ = -0.6 instead of -1. This is somewhat speculative, but since the user specifically mentions WES, we want the agent to make that trade-off. In short, we expect **fewer steps per success** (maybe our agent might take ~1.2× human steps on easy tasks, vs baseline’s 1.4×) and **quicker failure** when doomed. These improvements could make our agent rank higher on the OSWorld-Human leaderboard relative to its raw success rate.
  - A potential **bottleneck** is the vision understanding of Qwen-3 8B. If it mis-reads UI text or doesn’t comprehend an icon, it may choose wrong actions. This could cause failures or extra steps (corrective actions). Using the a11y text or providing tag descriptions is our way to mitigate this. Another bottleneck: Qwen-3’s context length and memory – we do keep prompts short, but it’s possible it forgets earlier parts of the plan for long tasks. Our plan injection should help, but the model might still wander if the task is too long for its understanding. In those cases, we rely on reflection as a fallback.
- **Future Optimization Directions:**
  1. **Enhanced Vision-Text Coordination (SoM Toolbox):** We could develop a small “toolbox” of utility functions accessible to the agent for common GUI queries. For example, a *“FindElement(name)”* tool that searches the a11y tree for a given text and returns the mark or coordinate. Or a *“ReadScreen()”* OCR tool for cases where a dialog text needs reading. In an interactive agent framework, we could integrate these as tool calls (Agent-S style). For now, we did a bit of this deterministically in the Grounder. But making it part of the reasoning (model explicitly asks for an element by keyword) could improve reliability, especially for dynamic content. Training or fine-tuning Qwen with such tools in the loop could be considered.
  2. **Fine-tuned Grounding Model:** Instead of purely heuristic mapping of marks, one could train a smaller model (or even a heuristic algorithm) to better interpret the accessibility tree and screenshot together. For instance, a model that given a text query (“OK button”) and the current UI, outputs the bounding box of that element. This could be like a neural UI locator. If available, the agent could consult this model when unsure (like if tags aren’t provided for some reason). The OSWorld-G benchmark (mentioned in search results) might be exactly about such grounding improvements. Incorporating that (if open-source) could significantly boost an 8B agent’s accuracy.
  3. **Learning from Experience:** Over time, the agent could build a memory of how tasks are solved. For example, store trajectories of successful attempts (could use the human references too). Then, for a new task, it could retrieve similar tasks and either adjust its plan or guide the LLM with “Here’s an example of a similar task’s solution.” This is meta-level optimization requiring infrastructure (experience replay or fine-tuning). In an offline sense, one could fine-tune Qwen-3 on OSWorld-Human trajectories so that it has in-domain knowledge. This might yield a specialized model that performs far better than a generic one. Even without full fine-tuning, a lightweight memory (like caching the plan for a known task ID) can help: if the agent encounters the same task again, it can reuse what worked or avoid what failed. Agent-S3 might have some component of learning or at least manual rule tuning from past runs; our current design is zero-shot for each task, so there’s room for improvement here.
  4. **Concurrency and Parallelism:** For efficiency in wall-clock time (not just step count), one could parallelize some operations. For example, while the agent is “waiting” for a page load, the Grounder could pre-fetch any updated a11y tree in the background, or a vision module could pre-scan for certain icons. Also, using vLLM’s ability to batch prompts, if we had multiple agents or multiple candidate actions to evaluate, we could do so in one go. Our design doesn’t explicitly cover this, but it’s an idea for speeding up large-scale evaluation or exploring multiple action hypotheses.
  5. **Refinement of Prompting:** Continually refine the prompts given model outputs. For instance, if we notice the model often outputs in a wrong format or tends to verbose thoughts, we can adjust the system prompt to be stricter (“No explanations outside JSON!”). If it doesn’t group actions enough, we could add a few-shot example in the system prompt showing grouping. These prompt tweaks can significantly alter performance and would be an iterative optimization process.

In conclusion, our Qwen-3 VL agent is **simpler and more lightweight** than the baseline heavy models, with a focus on *structured action output and efficient planning*. We expect slightly lower raw success due to model size, but much better efficiency (fewer steps) – potentially yielding a competitive showing on the WES metrics. By adopting strategies from Agent-S (modularity, memory, grounding) and tailoring them to an 8B model, we’ve created a foundation that can be further enhanced with the above suggestions. With additional tools or training, this agent could narrow the performance gap while retaining its speed advantage, moving closer to the goal of **fast and smart** computer-use autonomy.