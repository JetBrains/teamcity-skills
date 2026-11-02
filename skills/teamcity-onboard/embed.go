// Package teamcityonboard embeds the teamcity-onboard skill.
package teamcityonboard

import "embed"

// FS holds the skill with SKILL.md at its root.
//
//go:embed SKILL.md references
var FS embed.FS
