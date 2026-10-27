Do not quote me, unless i explicitly ask you to.

No comments, no docstrings,. no git commit messages

Agents are not allowed to edit this file in any circumstances. 

Simplicity is usually better. Note opportunities for it when possible.

Fallbacks are usually bad. Note opportunities to remove them when possible. 

Logging timings at least on function entry or exit should be done when possible.

Testing can be built during development but must be deleted as part of completion and should never be commited. 

Handling git and keeping it clean and organized and workable is part of your tasks

If using subagents, you are responsible for making sure they don't run too long. Set timeouts as nessesary, make sure they document enough so that you can tell if they are blocked or going in circles.

Avoid treating this project as a file dump. Files here eed to have ongoing use to the project. models, reports, and other files that are not helpful on an ongoing purpose should be placed elsewhere.

No git commit attribution allowed ever. no branch names that include codex ever.

claim attributes can only be single values, either a numerical or a flat categorical.
