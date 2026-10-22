# Living Dungeon: six major development passes

This is a scope plan, not a promise of six complete commercial-quality releases.
Each pass targets a playable Android APK and is validated separately.

1. **Foundation / Godot 0.4**: independent Godot project, dark procedurally drawn tiles, smooth character interpolation, drag/pinch camera, speed/pause, autosimulation, save/load. Keep Java 0.3 intact.
2. **Civilizations**: settlements, faction boundaries, resource gathering, work priorities, construction, recruitment and supply constraints.
3. **Characters**: persistent character IDs, jobs, traits, individual goals, memory, relationships, inventories, skill growth.
4. **Magic and calamities**: spells, necromancy, monster ecology, unique bosses and catastrophic world events.
5. **World editor / god mode**: place actors, edit terrain, intervene in diplomacy, spawn invasions and see causal event log.
6. **Scale & persistence**: chunk simulation, far-away simplified AI, longer world history, performance profiling, Android quality and stability.

The first foundation implementation is in `projects/dungeon_godot/`. The project is **separate** from `projects/dungeon/` and should be exported using `Build Living Dungeon Godot APK`, not the Java `build.yml` workflow.

**Verification requirements**:
- Godot editor command parses/imports scenes without script errors.
- Godot Android export produces `Living-Dungeon-Godot-APK`.
- APK is installed and opened on Android before any version is described as playable.
- No generated art sheets have been integrated into this first Godot project; graphics are procedural placeholders.
