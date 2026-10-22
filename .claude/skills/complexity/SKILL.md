---
name: complexity
description: complexity is an ever occuring issue in software development that we want to mitigate and reduce. Use the skill for knowledge and what to look out for in terms of what complexity is, symptoms, how to quanitify it, and what practices create it. Think about complexity from a human developers point of view.
---

1. Complexity: is anything related to the structure of a software system that makes it hard to understand and modify the system. 
2. When code is hard to read and understand what is happening without a large amount of effort it is complex.
	1. When code is unable to be improved or changed without a large amount of effort or creation of additional bugs, it is complex.
3. Assigning a quantitative value to it.
$$
	 
C = \sum_{p} C_p T_p
$$
In other words, Complexity of the system is equal to the Sum of each part weighted by the time developers spend working on them. 

1. **Symptoms of complexity**:
	1. Change amplification - how many places a piece of functionality has to be updated for a change. If feature X sprawls across 10 different files, it is complex to locate each correlated piece of code for feature X and each of those files and update it correctly. Leading to additional bugs.
		1. i.e putting all web elements in one central location.
	2. Cognitive Load: 
		1. The more the developer has to know the more cognitive load. If the developer has to remember 10 word of mouth details about a feature it is easy to forget one.
		2. More lines of code is not always worse if it is easier to understand.
			1. If code can be condensed down to 3 lines, but it is hard for other developers to understand what the code is doing , it may be more effective in 10 easily understandable lines.
      2. The `caveman code` skill touches on some of this.
	3. Unknown-Unknowns
		1. These are non obvious bits of information in a system that a developer may not know to update unless they are told about them. The system is non-obvious without reading every line of code in the system, which is not practical for any system of size. 
			1. For example if every page except 3 on a website use the main css components. You make a change to the main components expecting every page to update, leaving the other 3 unchanged.
	4. Complexity comes from dependencies and obscurities
		1. The more dependencies and non obvious code, the more complexity.
		2. Vague naming, unclear links, multiple adapters between dependencies, create complexity. 
			1. Complexity grows incrementally over time.

## How to apply these things
1. Calculate the complexity of features by time spent on github commits etc. in our products. 
C = SUM(workflows(chat)*0.5, workflows(DAG)*0.2) 
  - If not avaialble, create an estimate of human hours it will take to maintain a piece of functionality.
2. Functionality should be grouped tightly togethter. Even when following the modularity approach and splitting complexity into its own encapsulated files, it should be clearly grouped together in it's own directory so it is easy to find.
3. Make the system obvious , whether through code, comments, variable and function naming, docstrings, documentation.
4. An addition to documentation, each directory in the repo containing functionality, should have a README, documenting assumptions, edge cases, and need to know information to be passed on from developer to developer.