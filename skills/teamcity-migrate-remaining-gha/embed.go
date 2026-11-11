// Package teamcitymigrateremaininggha embeds the remaining GitHub Actions migration skill.
package teamcitymigrateremaininggha

import "embed"

// FS holds the skill with SKILL.md at its root.
//go:embed SKILL.md
var FS embed.FS
