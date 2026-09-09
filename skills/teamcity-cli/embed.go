// Package teamcitycli embeds the teamcity-cli agent skill so a Go consumer can
// ship this skill alone, without pulling in the other skills in this
// repository. Go links only imported packages, so an unimported skill costs a
// consumer nothing.
//
// FS is rooted at the skill itself (SKILL.md at the top level), which is the
// layout skill installers expect for a single skill.
package teamcitycli

import "embed"

// FS holds the whole skill: SKILL.md plus its references and sub-agents.
//
// _agents needs naming explicitly — a bare directory pattern skips entries
// beginning with "." or "_", which would silently drop the sub-agents.
//
//go:embed SKILL.md
//go:embed all:references
//go:embed all:_agents
var FS embed.FS
