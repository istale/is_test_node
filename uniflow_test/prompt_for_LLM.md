You are taking over a project built on a **Registry-based Modular Execution Framework**.  
All module information is centrally defined in `a0_registry/TOOL_INDEX.json`, which serves as the **Single Source of Truth (SSOT)**.

Steps:
1️⃣ Read `a0_registry/TOOL_INDEX.json` 
   • Record each tool’s `name`, `module`, `env_file`, `language`, `version`, and its declared `exports` or `callables`.  
   • If any field is missing, malformed, or inconsistent, mark it with ⚠️ and describe the expected content.

2️⃣ Do **not** open or scan source files unless verification is explicitly requested.  
   The registry is authoritative for all metadata, I/O contracts, and callable interfaces.

3️⃣ Summarize the registry contents in a structured, human-readable form:
      Module Inventory: 
      <tool_name>
         module: <import_path>
         env: <env_file_path>
         run_command: <run_command> (if NA should refer to run_shell_template)
         run_shell_templage <run_shell_template> (if NA should refer to run_command)
         callables: [func1, func2]
         usage: <short note or ⚠️>

4️⃣  Report any ⚠️ issues, but **do not** generate or modify code until a new system design is given.

5️⃣ When the user provides a **new system design or specification**,  
   • Create a new subdirectory using the next available prefix (e.g. `c01_`, `c02_`, `c03_`, …).  
   • Generate all related implementation code, configs, and docs inside that folder.  
   • Keep existing files untouched unless the user explicitly requests modification.

Do **not** modify or create any files yet.  
Wait for the next design or implementation request before coding.