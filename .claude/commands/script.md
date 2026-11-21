---
description: Write a full video script into scripts/pending/ (topic or idea number from ideas.md)
---
Topic: $ARGUMENTS
(If no topic is given, use the top unused idea in `ideas.md`.)

1. Read `channel/bible.md` and the last 3 scripts in `scripts/done/` so this one is different in structure and examples.
2. Research the topic on the web. Note a source for every fact and number.
3. Write the script in the format described in `CLAUDE.md`:
   - hook in the first 2 sentences, then the promise of the video
   - every section heading as `# Label | short Urdu card title` (under 35 characters)
   - spoken words only in the body; visual notes as [B-roll: ...]
   - one `[MY TAKE: ...]` placeholder where the owner adds their own view
   - "Sources" at the end, every line inside [square brackets]
   - description with chapters, 8 to 15 tags, thumbnail_text of 4 words or fewer
   - `approved: false`
   - If $ARGUMENTS asks for a Short: `format: short`, 70 to 110 spoken words (under 60 seconds), one single point, hook in the first sentence, end by pointing to the related long video
4. Save it as `scripts/pending/YYYY-MM-DD-short-topic.md` (date = planned publish date).
5. Tell me the word count, estimated length in minutes, and what I need to review or add before I approve it.
