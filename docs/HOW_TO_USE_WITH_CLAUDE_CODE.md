# How to Use These Documents with Claude Code

## 📋 What You Have

1. **CLAUDE_CODE_CONTEXT.md** → Full context document (main reference)
2. **QUICK_REFERENCE.md** → Quick lookup card
3. This file → Setup instructions

---

## 🚀 Setup in Claude Code

### Option 1: Add as Project Context (Recommended)

**In Claude Code:**

1. Open your project folder
2. Add both `.md` files to your project root
3. Claude Code automatically reads them as context
4. Start working!

**Usage:**
```bash
# Claude Code will have context about AG2 system
# Just start giving instructions:

"Implement player statistics dashboard"
```

---

### Option 2: Reference in Prompt (Manual)

**First message to Claude Code:**

```
I'm working with an AG2 multi-agent system. Read CLAUDE_CODE_CONTEXT.md for full details.

Context summary:
- AG2 agents handle coding autonomously
- I give high-level instructions
- Agents commit to Git automatically
- My role: Tech lead, not coder

Current task: [Your instruction here]
```

---

### Option 3: Add to Custom Instructions (Persistent)

**In Claude Code Settings:**

Add this to your custom instructions:

```
IMPORTANT: I'm working with an AG2 multi-agent development system.

CONTEXT:
- Project: LOL ELO Ranking System
- Agents: CaptainAgent + specialized team
- They handle implementation autonomously
- I provide high-level direction only

MY ROLE:
- Give feature-level instructions
- Review agent work
- Set priorities
- Provide strategic direction

DO NOT:
- Write implementation code for me
- Provide code snippets to copy-paste
- Give micro-level instructions

INSTEAD:
- Help me formulate clear high-level instructions
- Review agent commits with me
- Suggest features to implement
- Analyze architecture decisions

Reference: CLAUDE_CODE_CONTEXT.md (in project root)
```

---

## 💬 Example Claude Code Session

### Session 1: Project Analysis

**You:**
```
I just connected to the AG2 system. Help me understand the current project state.

Instruction for agents: "Inspect the entire project and provide comprehensive architecture overview"
```

**Claude Code:**
```
Based on the AG2 context, I'll help you formulate this instruction.

Since you're working with autonomous agents, your instruction is good! 
The agents will:
1. Scan all project files
2. Analyze structure
3. Identify components
4. Report architecture

Give this instruction via the Replit UI and the agents will work autonomously.

After they report back, I can help you:
- Understand the architecture they found
- Identify areas for improvement
- Plan next features
```

---

### Session 2: Feature Planning

**You:**
```
The agents finished the inspection. The project has:
- ELO calculator (working)
- SQLite database (basic)
- Streamlit dashboard (minimal)
- Some tests

I want to add a tier/ranking system. How should I instruct the agents?
```

**Claude Code:**
```
Perfect! Based on the AG2 context, here's my recommendation:

HIGH-LEVEL INSTRUCTION (Give this to agents):
"Implement a tier system where players are automatically ranked into tiers 
(Bronze, Silver, Gold, Platinum, Diamond) based on their ELO rating. 
The dashboard should display each player's tier."

This instruction is good because:
✅ Describes WHAT you want (tier system)
✅ Provides requirements (5 tiers, auto-assignment)
✅ States desired outcome (dashboard display)
❌ Doesn't specify HOW to implement

The agents will:
1. CaptainAgent: Plan the implementation
2. BackendDev: Create tier calculation logic
3. DatabaseSpecialist: Add tier column/table
4. FrontendDev: Update dashboard UI
5. QAEngineer: Write tests

Expected commits: 3-5 automatic commits

After they finish, we can review and iterate!
```

---

### Session 3: Bug Fixing

**You:**
```
The tier system was implemented but there's a bug - some players 
show the wrong tier. How do I get agents to fix this?
```

**Claude Code:**
```
For bug fixes with autonomous agents, be descriptive but not prescriptive.

GOOD INSTRUCTION:
"The tier system has a bug where some players display incorrect tiers. 
Investigate the tier calculation logic and fix the issue. Verify with tests."

This lets agents:
1. Investigate root cause (might not be what you think!)
2. Decide best fix approach
3. Implement solution
4. Add tests to prevent regression

AVOID:
❌ "Change the if statement in tier_calculator.py line 45"
(Too specific, removes agent autonomy)

After they fix it, check the commit messages - they'll explain what was wrong.
```

---

## 🎯 Best Practices with Claude Code

### 1. Use Claude Code for Strategy

**Claude Code helps you:**
- ✅ Formulate clear instructions for agents
- ✅ Review architectural decisions
- ✅ Analyze agent commits
- ✅ Plan feature roadmaps
- ✅ Understand tradeoffs

**Claude Code does NOT:**
- ❌ Write code (agents do that)
- ❌ Execute commands (agents do that)
- ❌ Manage Git (agents do that)

---

### 2. Review Cycle with Claude Code

```
1. Agents complete work → Commits on GitHub

2. YOU + CLAUDE CODE: Review together
   "Claude, help me review these commits: [paste commit messages]"

3. CLAUDE CODE: Analyzes changes
   "The agents implemented X by doing Y. Looks good because Z."
   "Potential concern: A. You might want to ask agents to improve B."

4. YOU: Decide next step
   - Accept → Move to next feature
   - Refine → Give feedback to agents
   - Reject → Ask agents to try different approach
```

---

### 3. Planning Features with Claude Code

**Workflow:**

```
YOU: "I want to add [complex feature]"

CLAUDE CODE: 
"Let me help break this down into a clear instruction for the agents...

Based on your requirements, here's what you should tell them:
[Formulated instruction]

This will likely involve:
- Component A (BackendDev)
- Component B (DatabaseSpecialist)  
- Component C (FrontendDev)

Expected complexity: Medium
Estimated commits: 5-8"

YOU: [Give instruction to agents via Replit UI]

AGENTS: [Work autonomously]

CLAUDE CODE: [Helps you review results]
```

---

## 📊 Workflow Diagram

```
┌─────────────────────────────────────────────┐
│  YOU (Tech Lead)                            │
│  ↓ Strategy & Direction                     │
├─────────────────────────────────────────────┤
│  CLAUDE CODE (Advisor)                      │
│  ↓ Helps formulate instructions             │
│  ↓ Reviews agent work                       │
│  ↓ Suggests improvements                    │
├─────────────────────────────────────────────┤
│  REPLIT UI (Command Center)                 │
│  ↓ You give instructions here               │
├─────────────────────────────────────────────┤
│  AG2 AGENTS (Implementation Team)           │
│  ↓ CaptainAgent + Specialists               │
│  ↓ Autonomous coding                        │
│  ↓ Git commits                              │
├─────────────────────────────────────────────┤
│  GITHUB (Source Control)                    │
│  ↓ Review commits here                      │
└─────────────────────────────────────────────┘
       ↑
       └─── YOU + CLAUDE CODE review together
```

---

## 🔍 Common Questions

### Q: When should I use Claude Code vs just giving instructions to agents?

**A:** 
- **Use Agents for:** Implementation, coding, debugging, testing
- **Use Claude Code for:** Strategy, planning, review, learning

### Q: Can Claude Code execute commands on Replit?

**A:** No. Claude Code is for planning and analysis. Give execution commands via Replit UI to agents.

### Q: Should I paste agent responses into Claude Code?

**A:** Yes! That's a great use case:

```
"Claude, the agents reported this architecture:
[paste agent response]

Help me understand it and suggest next steps."
```

### Q: Can Claude Code and agents work together?

**A:** Not directly. Think of it as:
- **Claude Code** = Your advisor/consultant
- **AG2 Agents** = Your development team
- **You** = The bridge between them

---

## 🚀 Quick Start Checklist

Setting up for first time:

- [ ] Place both `.md` files in project root
- [ ] Open Claude Code in project folder
- [ ] Verify Claude Code can see the context files
- [ ] Give first instruction to agents (via Replit)
- [ ] Use Claude Code to review results
- [ ] Iterate!

---

## 💡 Pro Tips

1. **Keep QUICK_REFERENCE.md open** in a tab for fast lookup

2. **Update CLAUDE_CODE_CONTEXT.md** as project evolves
   - Ask agents to update it: "Update the context document with current architecture"

3. **Use Claude Code for learning**
   - "Explain what the agents did in this commit"
   - "Why did they choose this approach?"

4. **Paste commit messages** into Claude Code for analysis
   - Gets you up to speed fast
   - Helps understand agent decisions

5. **Ask "why" questions** to Claude Code
   - "Why would agents implement it this way?"
   - "What are the tradeoffs of this design?"

---

## 🎓 Remember

**Your Role:** Tech Lead / Product Owner  
**Claude Code's Role:** Senior Advisor  
**AG2 Agents' Role:** Development Team

You don't code anymore - you **lead**.

---

**Now you're ready!** Start with a simple instruction and see how the agents work. Use Claude Code to help plan and review.

Good luck! 🚀
