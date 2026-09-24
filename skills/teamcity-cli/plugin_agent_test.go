package teamcitycli_test

import (
	"os"
	"path/filepath"
	"testing"
)

// The babysit-build sub-agent has to exist in two places, because the two ways
// of shipping it look in different locations:
//
//   - skills/teamcity-cli/_agents/ — read by instill when the teamcity CLI runs
//     `skill install`, which extracts it to the agent's .claude/agents/
//   - agents/ at the repository root — read by Claude Code when this repository
//     is installed as a plugin
//
// A symlink does not work: the plugin loader does not follow it, and the
// sub-agent silently fails to load. So the file is duplicated, and this test
// keeps the copies identical — without it, the plugin would quietly ship a
// stale sub-agent.
func TestPluginAgentMatchesSkillAgent(t *testing.T) {
	const rel = "_agents/babysit-build.md"
	pluginCopy := filepath.Join("..", "..", "agents", "babysit-build.md")

	inSkill, err := os.ReadFile(rel)
	if err != nil {
		t.Fatalf("reading skill copy: %v", err)
	}
	inPlugin, err := os.ReadFile(pluginCopy)
	if err != nil {
		t.Fatalf("reading plugin copy: %v", err)
	}
	if string(inSkill) != string(inPlugin) {
		t.Errorf("%s and %s have diverged — copy the skill version over the plugin one", rel, pluginCopy)
	}
}
