Please analyze and fix the Github issue: $ARGUMENTS.

Follow these steps:

# PLAN
1. Use 'gh issue view' to get the issue details
2. Understand the problem described in the issue
3. Ask clarifying questions if necessary
4. Understand the prior art for this issue
- Search the scratchpads, read the first two lines of the file only for previous thoughts related to the issue
- Search PRs to see if you can find history on this issue
- Search the codebase for relevant files
5. Think harder about how to break the issue down into a series of small,
manageable tasks.
6. Document your plan in a new scratchpad
    - include the issue name in the filename
    - include a link to the issue in the scratchpad.
7. Make a 2 line summary of the scratchpad at the top of the file.

# CREATE
- Create a new branch for the issue
- Solve the issue in small, manageable steps, according to your plan.
- Commit your changes after each step.

# TEST
- Write at most 5 tests
- Run the full test suit to ensure you haven't broken anything
- If the tests are failing, fix them.
- Ensure that all tests are passing before moving to the next step
- Ensure that tests pass on CI on github too

# DEPLOY
- Open a PR and request a review.

Remember to use the Githun CLI ('gh') for all Github-related tasks.
