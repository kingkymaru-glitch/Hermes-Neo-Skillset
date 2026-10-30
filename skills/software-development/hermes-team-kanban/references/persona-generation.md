# Persona Generation System

How to generate and manage the 200+ persona library used in the Discussion Room.

## Generation Script

Personas are generated combinatorially from archetype × domain × experience level:

```python
import json, os, itertools

ARCHETYPES = [
    "Leader", "Creator", "Analyst", "Rebel", "Mentor",
    "Visionary", "Strategist", "Critic", "Builder", "Explorer",
    "Guardian", "Trickster", "Healer", "Warrior", "Sage",
    "Innovator", "Diplomat", "Perfectionist", "Minimalist", "Chaos Agent"
]

ALIGNMENTS = [
    {"name": "Good", "desc": "Supportive, optimistic, builds on ideas"},
    {"name": "Neutral", "desc": "Balanced, weighs pros and cons"},
    {"name": "Chaotic", "desc": "Disruptive, challenges everything, devil's advocate"},
    {"name": "Mixture", "desc": "Custom blend of support and challenge"}
]

TRAITS = [
    "Pragmatic", "Creative", "Data-Driven", "Empathetic", "Analytical",
    "Intuitive", "Systematic", "Spontaneous", "Detail-Oriented", "Big-Picture",
    "Risk-Averse", "Risk-Taking", "Patient", "Impatient", "Diplomatic",
    "Blunt", "Humorous", "Serious", "Optimistic", "Pessimistic",
    "Collaborative", "Independent", "Methodical", "Flexible", "Stubborn",
    "Curious", "Cautious", "Bold", "Reflective", "Action-Oriented"
]

EXPERIENCE_LEVELS = [
    {"name": "Novice", "desc": "Learning, asks fundamental questions"},
    {"name": "Intermediate", "desc": "Competent, balanced perspective"},
    {"name": "Expert", "desc": "Deep knowledge, sees patterns others miss"},
    {"name": "Master", "desc": "Decades of experience, wisdom-level insight"}
]

DOMAINS = [
    "Technology", "Business", "Design", "Science", "Psychology",
    "Philosophy", "Marketing", "Finance", "Engineering", "Arts"
]

# Generate 200 personas from the cross-product
personas = []
combos = list(itertools.product(
    range(len(ARCHETYPES)),
    range(len(DOMAINS)),
    range(len(EXPERIENCE_LEVELS))
))

for i, (arch_idx, dom_idx, exp_idx) in enumerate(combos[:200]):
    archetype = ARCHETYPES[arch_idx]
    domain = DOMAINS[dom_idx]
    experience = EXPERIENCE_LEVELS[exp_idx]
    alignment = ALIGNMENTS[i % len(ALIGNMENTS)]
    trait1 = TRAITS[i % len(TRAITS)]
    trait2 = TRAITS[(i + 7) % len(TRAITS)]

    name = f"{archetype} {domain} {experience['name']}"
    persona_id = f"p_{i:03d}"

    soul_text = f"""You are a {experience['name'].lower()}-level {archetype} specializing in {domain}.
Your alignment is {alignment['name']}: {alignment['desc']}.
Your core traits are {trait1} and {trait2}.

As this persona, you:
- Approach problems from a {domain.lower()} perspective
- Demonstrate {experience['name'].lower()}-level depth in your responses
- Lean toward {alignment['name'].lower()} interpretations
- Balance {trait1.lower()} thinking with {trait2.lower()} instincts
- Speak with the confidence of someone at {experience['name'].lower()} level in {domain}

Stay in character. Every response should feel like it comes from this specific persona."""

    personas.append({
        "id": persona_id,
        "name": name,
        "archetype": archetype,
        "domain": domain,
        "alignment": alignment["name"],
        "traits": [trait1, trait2],
        "experience": experience["name"],
        "soul": soul_text
    })

# Save to disk
with open(os.path.expanduser("~/.hermes/persona-library/personas.json"), "w") as f:
    json.dump(personas, f, indent=2)
```

## Adding More Personas

To add new personas beyond the initial 200:
1. Add new archetypes, domains, or traits to the lists above
2. Increase the slice limit from `[:200]` to a higher number
3. Re-run the script — it overwrites `personas.json` with the expanded set
4. The dashboard will automatically pick up the new count on next load

## Custom Persona

To create a one-off persona not in the library:
1. Construct the `soul` text following the template above
2. Append to `personas.json` with a unique ID
3. It appears in the dashboard dropdown immediately

## Persona Selection Storage

Each profile stores its active persona at:
- Default: `~/.hermes/personas/active_persona`
- Named profiles: `~/.hermes/profiles/<name>/personas/active_persona`

The file contains just the persona ID string (e.g., `p_042`). The dashboard reads this file and looks up the full persona details from `personas.json`.
