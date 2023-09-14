# Ataka Quick Command Cheat Sheet

The most important commands are listed below:

Submit flag manually:
`atk flag submit FLAG{N0WAYAAAAAAAAAAAAAAAAAAAAAAAAAB}`
Or simply `atk flag submit <ENTER> <PASTE output / flags> <CTRL-D>`

Update config:
`atk reload`

Create exploit template:
`atk exploit template <python/ubuntu>[:version] <directory>`

List services / flag ids:
`atk flag ids [--all-targets]`

Run exploit locally testing:
`atk exploit runlocal <directory> <service>`

Run exploit locally against everyone:
`atk exploit runlocal --all-targets <directory> <service>`

Create exploit on the server:
`atk exploit create <exploitName> <service>`

Upload exploit:
`atk exploit upload <exploitName> <yourName> <directoryWithDockerFile>`

Logs:
`atk exploit logs <exploitID> -n <numberOfIterations>`