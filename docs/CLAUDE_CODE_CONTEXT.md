# League of Legends ELO System - AG2 Project Context

**Version:** 1.0  
**Last Updated:** 2025-02-12  
**Project Type:** Multi-Agent Development System  

---

## 🎯 PROJECT OVERVIEW

### What This Is
This is a **League of Legends ELO Ranking System** being developed with **AG2 (AutoGen 2)** multi-agent system. The agents work **autonomously** to implement features, fix bugs, and improve the codebase.

### Your Role as Claude Code
You are working **alongside** an AG2 multi-agent team. Your job is to:
- Give **high-level instructions** to the agent team
- Review and understand what agents have done
- Provide strategic direction
- **NOT** to write all code yourself - let the agents do the work

---

## 🏗️ SYSTEM ARCHITECTURE

### Platform Stack
- **Development Environment:** Replit (cloud-based)
- **Source Control:** GitHub (with auto-sync)
- **Runtime:** Python 3.12
- **Database:** SQLite
- **Frontend:** Streamlit
- **Agent Framework:** AG2 (AutoGen 2) with CaptainAgent

### Agent Team Structure

```
CaptainAgent (Orchestrator)
├── ProjectLead
│   ├── Role: Coordinates agents, plans architecture
│   └── Autonomy: High - makes technical decisions
├── BackendDev
│   ├── Role: ELO logic, core algorithms, business logic
│   └── Autonomy: Full - implements features independently
├── DatabaseSpecialist
│   ├── Role: Schema design, queries, data integrity
│   └── Autonomy: Full - modifies DB without asking
├── FrontendDev
│   ├── Role: Streamlit dashboard, UI/UX
│   └── Autonomy: Full - builds interfaces independently
└── QAEngineer
    ├── Role: Testing, validation, bug detection
    └── Autonomy: Full - writes and runs tests

NOTE: CaptainAgent can CREATE new specialized agents if needed!
```

### Current Project Structure

```
project/
├── calculator/          # ELO calculation engine
│   └── (your existing code)
├── database/           # SQLite database layer
│   └── (your existing code)
├── dashboard/          # Streamlit frontend
│   └── (your existing code)
├── tests/              # Test suite
│   └── (your existing code)
├── requirements.txt    # Python dependencies
└── README.md          # Project documentation
```

**TODO:** Update this structure after first inspection by agents.

---

## 🤖 HOW TO WORK WITH THE AG2 SYSTEM

### ✅ CORRECT Approach - High-Level Instructions

Give **feature-level** instructions, not implementation details:

**GOOD Examples:**
```
"Implement a tier system with ranks: Bronze, Silver, Gold, Platinum, Diamond"

"The dashboard is slow - optimize it"

"Add input validation to prevent invalid ELO calculations"

"Create an API endpoint for recording match results"

"Fix the bug where ratings go negative"
```

**Why this works:**
- CaptainAgent plans the implementation
- Agents decide HOW to implement
- Multiple agents collaborate
- You get complete features, not code snippets

---

### ❌ INCORRECT Approach - Micro-Management

Don't give line-by-line instructions:

**BAD Examples:**
```
"Open calculator.py, find line 45, add if rating < 0: return 0"

"Import pandas at the top of database.py"

"Change the button color to blue in dashboard.py line 123"
```

**Why this fails:**
- Bypasses agent intelligence
- Wastes multi-agent capability
- You might as well code it yourself

---

## 📋 COMMAND PATTERNS

### Feature Implementation
```
"Implement [feature name]"
"Add [functionality] to [component]"
"Create a new [module/system] for [purpose]"
```

### Bug Fixing
```
"Fix [issue description]"
"Investigate why [unexpected behavior]"
"Debug [component] - [symptom]"
```

### Optimization
```
"Optimize [component] for performance"
"Reduce memory usage in [module]"
"Improve [metric] in [system]"
```

### Analysis
```
"Analyze the current [component] architecture"
"Review [code/system] for potential issues"
"What's the current state of [feature]?"
```

### Testing
```
"Write tests for [component]"
"Increase test coverage for [module]"
"Add integration tests for [workflow]"
```

---

## 🔄 WORKFLOW

### Typical Development Cycle

```
1. YOU → Give high-level instruction via Replit UI
   Example: "Implement player statistics page in dashboard"

2. CAPTAINAGENT → Analyzes & Plans
   - Breaks down into subtasks
   - Assigns to appropriate agents
   - Coordinates dependencies

3. AGENTS → Work Autonomously
   - BackendDev: Creates stats calculation functions
   - DatabaseSpecialist: Adds necessary queries
   - FrontendDev: Builds UI components
   - QAEngineer: Writes tests

4. GIT → Multiple commits happen automatically
   - "Add player stats calculation module"
   - "Create database queries for player stats"
   - "Implement stats dashboard page"
   - "Add tests for stats functionality"

5. YOU → Review on GitHub
   - Check commits
   - Test the feature
   - Provide feedback or new instructions

6. ITERATE → Next instruction
```

---

## 🎯 CURRENT PROJECT GOALS

### Completed Features
- [x] Basic ELO calculation engine
- [x] SQLite database setup
- [x] Initial dashboard
- [x] Core tests

**TODO:** Update this list as agents complete tasks.

### In Progress
- [ ] (Add current tasks here)

### Backlog / Ideas
- [ ] Tier/Rank system (Bronze, Silver, Gold, etc.)
- [ ] Match history visualization
- [ ] Player statistics dashboard
- [ ] API for external integrations
- [ ] Advanced analytics (win rate trends, etc.)
- [ ] Performance optimizations
- [ ] Comprehensive test coverage (>80%)
- [ ] Discord bot integration (future)

**TODO:** Add your priorities here.

---

## 🛠️ TECHNICAL SPECIFICATIONS

### ELO System Requirements

**Formula:**
```python
new_rating = old_rating + K * (actual_score - expected_score)
```

**Expected Score:**
```python
expected = 1 / (1 + 10^((opponent_rating - player_rating) / 400))
```

**K-Factor (Dynamic):**
- K = 32 for players with <30 games
- K = 24 for players with 30-100 games  
- K = 16 for players with >100 games

**Rating Bounds:**
- Minimum: 100
- Maximum: 3000
- Default (new player): 1200

**Match Results:**
- Win: actual_score = 1
- Loss: actual_score = 0
- Draw: actual_score = 0.5 (if supported)

### Database Schema (Current)

**TODO:** Agents should inspect and document actual schema here.

**Expected Tables:**
- `players` - Player information and current ratings
- `matches` - Match history
- `rating_history` - Historical rating changes

### Coding Standards

**TODO:** Agents will adapt to existing code style, but general guidelines:

- **Python Style:** PEP 8 compliant
- **Type Hints:** Use where applicable
- **Docstrings:** Google-style preferred
- **Testing:** pytest framework
- **Commits:** Descriptive messages, atomic changes
- **Branches:** Main branch is production-ready

---

## 🚨 IMPORTANT RULES

### Git Commits
- ✅ **Agents HAVE full Git access** - they commit and push directly
- ✅ **Autonomous commits** - no approval needed
- ✅ **Review commits on GitHub** - you review after the fact
- ⚠️ If agents break something, give instruction: "Revert last commit and fix [issue]"

### Agent Autonomy
- ✅ **Agents decide HOW** - you decide WHAT
- ✅ **Agents can create files, modify, delete** - full control
- ✅ **Agents can create new agents** - if CaptainAgent needs specialists
- ✅ **Agents work in parallel** - multiple agents can work simultaneously
- ⚠️ **Agents don't ask permission** - they make technical decisions

### Your Boundaries
- ✅ **Strategic decisions** - what features to build
- ✅ **Priority setting** - what to work on next
- ✅ **Quality review** - feedback on results
- ✅ **Architecture oversight** - major design decisions
- ❌ **Implementation details** - let agents figure this out
- ❌ **Code-level changes** - delegate to agents

---

## 📊 MONITORING & FEEDBACK

### Check Agent Progress

**Via Replit UI:**
- Real-time log shows agent activity
- See which agents are working
- View decisions and actions

**Via GitHub:**
- Check commit history
- Review code changes
- See feature branches (if used)

### Giving Feedback

**If agents did well:**
```
"Great work on the tier system! Now add tier badges to player profiles."
```

**If something needs fixing:**
```
"The tier calculation is wrong - Diamond should start at 2000 not 1800. Fix this."
```

**If you want different approach:**
```
"The stats page is too cluttered. Redesign with a cleaner, card-based layout."
```

---

## 🎓 LEARNING FROM AGENTS

### Agents as Teammates

Think of the AG2 system as **your development team**:

- **You** = Product Owner / Tech Lead
- **CaptainAgent** = Engineering Manager
- **Other Agents** = Senior Engineers

They're capable, autonomous, and don't need hand-holding.

### Trust the Process

- ✅ Start with simple tasks to build trust
- ✅ Gradually give more complex features
- ✅ Let agents surprise you with solutions
- ⚠️ Review but don't micromanage
- ⚠️ Accept their approach may differ from yours

---

## 🔧 TROUBLESHOOTING

### "Agents aren't doing what I want"

**Problem:** Instructions too vague or too specific

**Solution:**
- Too vague: "Make it better" → "Improve dashboard load time by optimizing database queries"
- Too specific: "Change line 42" → "Fix the bug where negative ratings appear"

### "Agents made mistakes"

**Problem:** Bugs introduced by autonomous work

**Solution:**
```
"The last commit broke [feature]. Analyze the issue and fix it."
```

Agents will:
1. Review their changes
2. Identify the problem
3. Fix it
4. Commit the fix

### "I want to undo something"

**Problem:** Don't like the direction agents took

**Solution:**
```
"Revert the tier system implementation and try a different approach: [explain approach]"
```

### "Need to check current status"

**Command:**
```
"What's the current state of the project? List all major components and their status."
```

Agents will inspect and report.

---

## 📞 DISCORD INTEGRATION (FUTURE)

**Status:** Not yet implemented

**When implemented, you'll be able to:**
- Send commands from mobile via Discord
- Get status updates in Discord channels
- Review agent work on-the-go
- Approve/reject major changes

**Workflow:**
```
Discord: /dev implement player rankings
Bot: Started task, 3 agents working...
Bot: Committed "Add ranking calculation"
Bot: Committed "Add rankings to dashboard"  
Bot: ✅ Task completed - 2 commits pushed
```

---

## 🚀 QUICK START GUIDE

### First Time Using This System

**Step 1:** Get familiar with current codebase
```
"Inspect the entire project and give me a comprehensive overview of the architecture."
```

**Step 2:** Test with small task
```
"Add a function to calculate average ELO across all players"
```

**Step 3:** Review the commit on GitHub

**Step 4:** Give medium complexity task
```
"Add player win/loss statistics to the dashboard"
```

**Step 5:** Scale up to full features
```
"Implement a complete tier system with automatic tier assignment"
```

### Daily Usage Pattern

**Morning:**
```
"What was completed yesterday? Show me the commits."
```

**During Day:**
```
"Priority 1: [Feature A]"
"Priority 2: [Feature B]"  
"Fix: [Bug C]"
```

**Evening:**
```
"Status update - what's in progress?"
```

---

## 📝 EXAMPLE SESSION

```
YOU:
"Implement a tier system. Players should be ranked Bronze, Silver, Gold, Platinum, Diamond based on their ELO rating."

CAPTAINAGENT:
Analyzing task... Breaking down into:
1. Define tier boundaries
2. Create tier calculation logic
3. Add tier column to database
4. Update dashboard to show tiers
5. Add tests

Delegating to: BackendDev, DatabaseSpecialist, FrontendDev, QAEngineer

[8 minutes later]

RESULT:
✅ Completed: Tier System Implementation
📦 Files changed: 7
💾 Commits: 4
  - "Add tier calculation module"
  - "Update database schema with tier column"
  - "Add tier display to dashboard"
  - "Add tier system tests"

🔗 Latest commit: abc123def

YOU:
"Great! Now add tier badges (icons) next to player names in the dashboard."

CAPTAINAGENT:
Working on it...

[3 minutes later]

✅ Completed: Tier Badge Icons
📦 Files changed: 2
💾 Commits: 1
  - "Add tier badge icons to player display"
```

---

## 🎯 SUCCESS METRICS

Track these to see if the AG2 system is working well:

- **Development Speed:** How fast do features get implemented?
- **Code Quality:** Are tests passing? Is code maintainable?
- **Commit Quality:** Are commits atomic and well-described?
- **Agent Effectiveness:** Do they understand requirements correctly?
- **Your Time Saved:** Are you doing less coding, more directing?

**Goal:** You spend 80% time on strategy, 20% on review. Agents do 100% of coding.

---

## 📚 REFERENCE

### Key Concepts

**CaptainAgent:** The orchestrator who coordinates other agents

**Agent Library:** The pool of available specialized agents

**Autonomous Mode:** Agents work without human approval at each step

**High-Level Instructions:** Feature-level commands, not code-level

**Git Integration:** Agents commit directly to repository

### Useful Commands

**Status Check:**
```
"What's the current status of [component/feature]?"
"Show me what agents are working on"
```

**Code Review:**
```
"Review [component] for potential improvements"
"Analyze performance of [module]"
```

**Planning:**
```
"What would it take to implement [feature]?"
"Break down [large feature] into milestones"
```

---

## 🔄 KEEPING THIS DOCUMENT UPDATED

This document should evolve with your project:

**Update when:**
- ✅ Project structure changes
- ✅ New major features completed
- ✅ Team discovers new best practices
- ✅ Workflow processes improve
- ✅ New agents added to team

**How to update:**
```
"Update the Claude Code context document to reflect [changes]"
```

Agents will update this file and commit it.

---

## 💡 FINAL TIPS

1. **Start small, scale up** - Build trust with simple tasks first

2. **Be patient** - Autonomous agents take time to analyze and plan

3. **Review commits regularly** - Catch issues early

4. **Give clear context** - "Why" helps agents make better decisions

5. **Iterate** - First version might not be perfect, refine with feedback

6. **Trust the process** - Agents often find solutions you didn't consider

7. **Think in features** - Not in code changes

8. **Leverage the team** - Multiple agents = parallel work on complex features

---

**Remember:** You're not coding anymore. You're **leading a development team**. 

Give direction, set priorities, review results. Let the agents handle implementation.

---

**Document End**

*Generated for Claude Code integration with AG2 Multi-Agent System*  
*Project: LOL ELO Ranking System*  
*Version: 1.0 - Initial*
