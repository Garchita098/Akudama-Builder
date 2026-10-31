shader_type canvas_item;
render_mode blend_mix, unshaded;

void fragment() {
	vec2 uv = UV * 2.0 - 1.0;
	uv.x *= 0.78;
	float v = dot(uv, uv);
	float a = smoothstep(0.28, 1.15, v) * 0.72;
	COLOR = vec4(0.01, 0.008, 0.02, a);
}
