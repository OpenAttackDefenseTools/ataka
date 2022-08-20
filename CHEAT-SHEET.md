# Ataka Quick Command Cheat Sheet

The most important commands are listed below:

Submit flag manually:
`atk flag submit FLAG{N0WAYAAAAAAAAAAAAAAAAAAAAAAAAAB}`

Update config:
`atk reload`

Create exploit template:
`atk exploit template <python/ubuntu> <directory>`

Run exploit locally:
`atk exploit runlocal --all-targets <directory> <service> <exploitId>`

Create exploit on the server:
`atk exploit create <exploitName> <service>`
ATTENTION: exploitName: no uppercase letters, no underscores

Upload exploit:
`atk exploit upload <exploitName> <yourName> <directoryWithDockerFile>`
-> returns exploitID

Run exploit: 
`atk exploit activate <exploitID>`

Logs:
`atk exploit logs <exploitID> -n <numberOfIterations>`