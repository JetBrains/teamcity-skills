// Package migratetoteamcity embeds the migrate-to-teamcity agent skill so a Go
// consumer can ship this skill alone, without pulling in the other skills in
// this repository. Go links only imported packages, so an unimported skill
// costs a consumer nothing.
//
// FS is rooted at the skill itself (SKILL.md at the top level), which is the
// layout skill installers expect for a single skill.
package migratetoteamcity

import "embed"

// FS holds the whole skill: SKILL.md plus its references. This skill ships no
// sub-agents, so there is no _agents pattern here.
//
//go:embed SKILL.md
//go:embed all:references
var FS embed.FS
