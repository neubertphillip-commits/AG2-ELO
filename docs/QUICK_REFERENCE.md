# Claude Code - AG2 Quick Reference Card

## 🎯 Your Role
You **direct** the agent team. You don't code - agents code.

---

## ✅ DO THIS

### Give High-Level Instructions
```
✅ "Implement tier system with Bronze-Diamond ranks"
✅ "Fix the performance issue in the dashboard"
✅ "Add player statistics page"
✅ "Create API for match recording"
```

### Think in Features, Not Code
```
✅ "The search is too slow" → Agents optimize
✅ "Dashboard needs a dark mode" → Agents implement
✅ "Players need profile pages" → Agents build
```

---

## ❌ DON'T DO THIS

### Avoid Micro-Management
```
❌ "Open file X, line Y, change Z"
❌ "Import pandas at the top"
❌ "Add a semicolon on line 42"
```

### Don't Write Code Yourself (Unless Testing)
```
❌ Writing implementation details
❌ Providing code snippets to copy
❌ Debugging line-by-line
```

---

## 🎯 Command Templates

### Implementation
```
"Implement [feature]"
"Add [functionality] to [component]"
"Create [new system] for [purpose]"
```

### Bug Fixing
```
"Fix [issue description]"
"Debug why [problem occurs]"
"Investigate [unexpected behavior]"
```

### Optimization
```
"Optimize [component]"
"Improve performance of [system]"
"Reduce load time for [feature]"
```

### Analysis
```
"Analyze [component] architecture"
"Review [system] for issues"
"What's the current state of [feature]?"
```

---

## 🤖 Agent Team

- **CaptainAgent** → Plans & coordinates
- **ProjectLead** → Architecture & decisions
- **BackendDev** → Core logic & algorithms
- **DatabaseSpecialist** → DB & queries
- **FrontendDev** → UI & dashboard
- **QAEngineer** → Tests & validation

**Note:** CaptainAgent creates new agents if needed!

---

## 📊 Workflow

```
1. YOU: "Implement feature X"
   ↓
2. CAPTAINAGENT: Plans & delegates
   ↓
3. AGENTS: Work autonomously
   ↓
4. GIT: Auto-commits (multiple)
   ↓
5. YOU: Review on GitHub
   ↓
6. ITERATE: Next instruction
```

---

## 🚨 Key Rules

✅ Agents have **full Git access** - they commit directly  
✅ Agents work **autonomously** - no approval needed  
✅ Agents make **technical decisions** - you make strategic  
✅ **Review after** - not approve before  
⚠️ If broken: "Revert and fix [issue]"

---

## 💡 Quick Tips

1. **Start small** → Build trust
2. **Be patient** → Analysis takes time
3. **Clear context** → Better results
4. **Think features** → Not code
5. **Trust agents** → They're capable

---

## 🔍 Useful Commands

**Status:**
```
"What's the current status?"
"Show me what agents are working on"
```

**Review:**
```
"Review the last changes"
"Analyze [component] for issues"
```

**Planning:**
```
"What's needed for [feature]?"
"Break down [large task] into steps"
```

---

## 🎓 Mindset Shift

❌ "I am a coder"  
✅ "I am a tech lead"

❌ "I write the code"  
✅ "I set the direction"

❌ "I fix every bug"  
✅ "I delegate to agents"

---

**Think:** You're managing a senior dev team, not coding solo.

---

*Keep CLAUDE_CODE_CONTEXT.md open for full details*
