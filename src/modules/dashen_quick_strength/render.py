from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .engine import score_to_rank

try:
    from overstats.src.modules.query_tool import get_cached_asset_path
except ModuleNotFoundError:
    from src.modules.query_tool import get_cached_asset_path


def _resolve_resource_dir() -> Path:
    here = Path(__file__).resolve()
    candidates = (
        here.parents[3] / "res",
        here.parents[4] / "overstats" / "res",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


RESOURCE_DIR = _resolve_resource_dir()
RANK_BREAKPOINTS = [1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500]
RANK_LABELS_CN = {
    "Bronze": "\u9752\u94dc",
    "Silver": "\u767d\u94f6",
    "Gold": "\u9ec4\u91d1",
    "Platinum": "\u767d\u91d1",
    "Diamond": "\u94bb\u77f3",
    "Master": "\u5927\u5e08",
    "Grandmaster": "\u5b97\u5e08",
    "Champion": "\u82f1\u6770",
    "Unranked": "\u672a\u5b9a\u7ea7",
}
RESULT_LABELS = {1: "\u80dc", -1: "\u8d1f", 0: "\u5e73"}
DEFAULT_STRENGTH_THEME = {
    "range_color": (140, 214, 255, 188),
    "line_color": (86, 154, 255, 255),
    "avatar_ring_color": (92, 151, 245, 255),
    "avatar_badge_text": "QS",
}
QUICK_STRENGTH_THEME = dict(DEFAULT_STRENGTH_THEME)
COMPETITIVE_STRENGTH_THEME = {
    "range_color": (232, 123, 156, 196),
    "line_color": (246, 144, 170, 255),
    "avatar_ring_color": (224, 105, 142, 255),
    "avatar_badge_text": "CS",
}


@dataclass(frozen=True)
class RenderedImage:
    content: bytes
    media_type: str = "image/png"


def render_quick_strength(
    *,
    player_name: str,
    bnet_id: str,
    summary: Dict[str, Any],
    matches: Sequence[Dict[str, Any]],
    avatar_bytes: Optional[bytes] = None,
    config: Optional[Dict[str, Any]] = None,
    theme: Optional[Dict[str, Any]] = None,
    title_text: str = "\u5feb\u901f\u5f3a\u5ea6\u6307\u6570",
    chart_title_text: str = "\u5feb\u901f\u5f3a\u5ea6\u8d8b\u52bf",
    match_scope_text: str = "\u5feb\u901f",
) -> RenderedImage:
    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise RuntimeError("render.py requires Pillow to output images") from exc

    scale = 2
    base_width = 1500
    base_height = 980
    width = base_width * scale
    height = base_height * scale
    canvas = Image.new("RGBA", (width, height), (11, 17, 28, 255))
    draw = _new_draw(canvas)
    fonts = _load_fonts(scale)
    render_config = config if isinstance(config, dict) else {}
    active_theme = _resolve_theme(theme)

    _draw_background(canvas, scale=scale)
    _draw_panel(
        draw,
        (36 * scale, 24 * scale, width - 36 * scale, 142 * scale),
        fill=(14, 22, 36, 215),
        outline=(47, 62, 88, 255),
        radius=14 * scale,
    )
    _draw_panel(
        draw,
        (36 * scale, 154 * scale, width - 36 * scale, 860 * scale),
        fill=(12, 19, 31, 225),
        outline=(47, 62, 88, 255),
        radius=14 * scale,
    )
    _draw_panel(
        draw,
        (36 * scale, 872 * scale, width - 36 * scale, height - 24 * scale),
        fill=(13, 20, 33, 225),
        outline=(47, 62, 88, 255),
        radius=14 * scale,
    )

    _draw_header(
        canvas,
        draw,
        player_name=player_name,
        bnet_id=bnet_id,
        summary=summary,
        avatar_bytes=avatar_bytes,
        fonts=fonts,
        scale=scale,
        theme=active_theme,
        title_text=title_text,
        match_scope_text=match_scope_text,
    )
    _draw_chart(
        canvas,
        draw,
        summary=summary,
        matches=matches,
        config=render_config,
        fonts=fonts,
        scale=scale,
        theme=active_theme,
        chart_title_text=chart_title_text,
    )
    _draw_footer(draw, fonts=fonts, scale=scale, theme=active_theme)

    output = BytesIO()
    canvas = canvas.resize((base_width, base_height), Image.LANCZOS)
    canvas.save(output, format="PNG")
    return RenderedImage(content=output.getvalue())


def _new_draw(image: Any) -> Any:
    from PIL import ImageDraw

    return ImageDraw.Draw(image, "RGBA")


def _resolve_theme(theme: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    resolved = dict(DEFAULT_STRENGTH_THEME)
    if isinstance(theme, dict):
        resolved.update({key: value for key, value in theme.items() if value is not None})
    return resolved


def _draw_background(canvas: Any, *, scale: int) -> None:
    from PIL import Image, ImageFilter

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = _new_draw(overlay)
    for idx in range(canvas.height):
        ratio = idx / max(canvas.height - 1, 1)
        red = int(8 + (22 - 8) * ratio)
        green = int(14 + (24 - 14) * ratio)
        blue = int(25 + (40 - 25) * ratio)
        draw.line((0, idx, canvas.width, idx), fill=(red, green, blue, 255))

    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    glow_draw = _new_draw(glow)
    glow_draw.ellipse(
        (-120 * scale, -80 * scale, 680 * scale, 520 * scale),
        fill=(34, 95, 179, 125),
    )
    glow_draw.ellipse(
        (canvas.width - 720 * scale, 30 * scale, canvas.width + 80 * scale, 600 * scale),
        fill=(29, 160, 187, 70),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=48 * scale))
    overlay.alpha_composite(glow)
    canvas.alpha_composite(overlay)


def _draw_panel(
    draw: Any,
    box: Tuple[int, int, int, int],
    *,
    fill: Tuple[int, int, int, int],
    outline: Tuple[int, int, int, int],
    radius: int,
) -> None:
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=max(2, radius // 10),
    )


def _draw_header(
    canvas: Any,
    draw: Any,
    *,
    player_name: str,
    bnet_id: str,
    summary: Dict[str, Any],
    avatar_bytes: Optional[bytes],
    fonts: Dict[str, Any],
    scale: int,
    theme: Dict[str, Any],
    title_text: str,
    match_scope_text: str,
) -> None:
    avatar_x = 70 * scale
    avatar_y = 32 * scale
    avatar_size = 78 * scale
    avatar = _open_avatar(
        avatar_bytes,
        size=avatar_size,
        ring_color=tuple(theme.get("avatar_ring_color") or DEFAULT_STRENGTH_THEME["avatar_ring_color"]),
    )
    if avatar is not None:
        canvas.paste(avatar, (avatar_x, avatar_y), avatar)
    else:
        draw.ellipse(
            (avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size),
            fill=(31, 52, 83, 255),
        )
        draw.text(
            (avatar_x + 26 * scale, avatar_y + 20 * scale),
            str(theme.get("avatar_badge_text") or "QS"),
            font=fonts["font_mono"],
            fill=(211, 230, 255, 255),
        )

    display_name = str(player_name or bnet_id or "Unknown").strip()
    raw_bnet_id = str(bnet_id or "").strip()
    if "#" in display_name:
        name_text, suffix_text = display_name.split("#", 1)
        suffix_text = f"#{suffix_text.strip()}"
    elif raw_bnet_id and "#" in raw_bnet_id:
        name_text, suffix_text = raw_bnet_id.split("#", 1)
        suffix_text = f"#{suffix_text.strip()}"
    else:
        name_text = display_name
        suffix_text = raw_bnet_id if raw_bnet_id and raw_bnet_id != display_name else ""

    title_x = 188 * scale
    draw.text(
        (title_x, 42 * scale),
        name_text,
        font=fonts["font_title"],
        fill=(242, 247, 255, 255),
    )
    if suffix_text:
        draw.text(
            (title_x + 2 * scale, 74 * scale),
            suffix_text,
            font=fonts["font_id_suffix"],
            fill=(186, 201, 224, 255),
        )
    draw.text(
        (190 * scale, 100 * scale),
        title_text,
        font=fonts["font_sub"],
        fill=(158, 178, 205, 255),
    )

    name_width = _measure_text(draw, name_text, fonts["font_title"])
    summary_x = max(500 * scale, title_x + name_width + 4 * scale)
    summary_x = min(summary_x, 660 * scale)
    _draw_summary_block(
        canvas,
        draw,
        x=summary_x,
        y=34 * scale,
        summary=summary,
        fonts=fonts,
        scale=scale,
        match_scope_text=match_scope_text,
    )


def _draw_summary_block(
    canvas: Any,
    draw: Any,
    *,
    x: int,
    y: int,
    summary: Dict[str, Any],
    fonts: Dict[str, Any],
    scale: int,
    match_scope_text: str,
) -> None:
    avg_score = float(summary.get("overall_avg_score") or 0)
    avg_rank = _rank_text_cn(summary.get("overall_avg_rank") or "Unranked")
    score_range = summary.get("score_range") if isinstance(summary.get("score_range"), dict) else {}
    range_min = int(score_range.get("min") or 0)
    range_max = int(score_range.get("max") or 0)
    match_count = int(summary.get("match_count") or 0)
    fallback_text = (
        "\u5df2\u542f\u7528\u4e0a\u8d5b\u5b63\u56de\u9000"
        if bool(summary.get("used_previous_season_fallback"))
        else "\u4f18\u5148\u4f7f\u7528\u5f53\u524d\u8d5b\u5b63"
    )

    icon_size = 54 * scale
    icon = _load_rank_flat_icon(avg_score, size=(icon_size, icon_size))
    text_x = x
    if icon is not None:
        canvas.paste(icon, (x, y + 4 * scale), icon)
        text_x += icon_size + 14 * scale

    draw.text(
        (text_x, y),
        "\u5e73\u5747\u6bb5\u4f4d\u4f30\u8ba1",
        font=fonts["font_summary_label"],
        fill=(155, 174, 198, 255),
    )
    draw.text(
        (text_x, y + 18 * scale),
        avg_rank,
        font=fonts["font_summary_rank"],
        fill=(238, 244, 252, 255),
    )

    score_text = (
        f"\u5e73\u5747\u5f3a\u5ea6 {avg_score:.1f}"
        if avg_score > 0
        else "\u5e73\u5747\u5f3a\u5ea6 --"
    )
    range_text = (
        f"\u5f3a\u5ea6\u8303\u56f4 {range_min} - {range_max}"
        if range_min > 0 and range_max > 0
        else "\u5f3a\u5ea6\u8303\u56f4 --"
    )
    draw.text(
        (text_x, y + 50 * scale),
        score_text,
        font=fonts["font_sub"],
        fill=(180, 198, 220, 255),
    )
    score_text_width = _measure_text(draw, score_text, fonts["font_sub"])
    draw.text(
        (text_x + score_text_width + 24 * scale, y + 50 * scale),
        range_text,
        font=fonts["font_sub"],
        fill=(180, 198, 220, 255),
    )
    draw.text(
        (text_x, y + 68 * scale),
        f"\u6700\u8fd1 {match_count} \u573a{match_scope_text}  \u00b7  {fallback_text}",
        font=fonts["font_meta"],
        fill=(132, 151, 176, 255),
    )


def _draw_chart(
    canvas: Any,
    draw: Any,
    *,
    summary: Dict[str, Any],
    matches: Sequence[Dict[str, Any]],
    config: Dict[str, Any],
    fonts: Dict[str, Any],
    scale: int,
    theme: Dict[str, Any],
    chart_title_text: str,
) -> None:
    x1 = 72 * scale
    y1 = 186 * scale
    x2 = 1428 * scale
    y2 = 828 * scale
    inner_left = x1 + 80 * scale
    inner_right = x2 - 42 * scale
    inner_top = y1 + 28 * scale
    inner_bottom = y2 - 74 * scale

    draw.text(
        (x1, y1 - 28 * scale),
        chart_title_text,
        font=fonts["font_panel_title"],
        fill=(235, 242, 252, 255),
    )
    draw.text(
        (x1 + 170 * scale, y1 - 24 * scale),
        "\u7c97\u6761=\u804c\u8d23\u533a\u95f4  \u7ec6\u6761=\u5168\u804c\u8d23\u533a\u95f4  "
        "\u6761\u5185\u7eff/\u7ea2\u77e9\u5f62=\u961f\u53cb/\u5bf9\u624b\u804c\u8d23\u5206",
        font=fonts["font_meta"],
        fill=(132, 151, 176, 255),
    )

    if not matches:
        draw.text(
            (inner_left, inner_top + 80 * scale),
            "\u6682\u65e0\u5feb\u901f\u6bd4\u8d5b\u6570\u636e",
            font=fonts["font_panel_title"],
            fill=(180, 190, 205, 255),
        )
        return

    score_values = _collect_chart_scores(matches)
    if not score_values:
        score_min = 1000
        score_max = 5000
    else:
        score_min = max(900, min(score_values) - 180)
        score_max = min(5100, max(score_values) + 180)
        score_min = (score_min // 100) * 100
        score_max = ((score_max + 99) // 100) * 100
        if score_max - score_min < 1200:
            center = (score_min + score_max) / 2
            score_min = int(center - 600)
            score_max = int(center + 600)

    def y_for(score: float) -> int:
        if score_max <= score_min:
            return int((inner_top + inner_bottom) / 2)
        ratio = (float(score) - score_min) / max(score_max - score_min, 1)
        ratio = max(0.0, min(1.0, ratio))
        return int(inner_bottom - ratio * (inner_bottom - inner_top))

    column_count = len(matches)
    if column_count <= 1:
        x_positions = [int((inner_left + inner_right) / 2)]
        label_width_limit = 180 * scale
    else:
        step_x = (inner_right - inner_left) / max(column_count - 1, 1)
        x_positions = [int(inner_left + idx * step_x) for idx in range(column_count)]
        label_width_limit = max(int(step_x - 14 * scale), 84 * scale)

    _draw_match_backdrops(
        canvas,
        draw=draw,
        matches=matches,
        config=config,
        x_positions=x_positions,
        inner_left=inner_left,
        inner_right=inner_right,
        inner_top=inner_top,
        inner_bottom=inner_bottom,
        scale=scale,
    )

    for breakpoint in RANK_BREAKPOINTS:
        if breakpoint < score_min or breakpoint > score_max:
            continue
        y = y_for(breakpoint)
        draw.text(
            (x1 + 2 * scale, y - 10 * scale),
            _score_to_rank_cn(breakpoint),
            font=fonts["font_axis"],
            fill=(142, 157, 181, 255),
        )

    all_role_width = max(8 * scale, 10)
    role_width = max(40 * scale, 44)
    range_color = tuple(theme.get("range_color") or DEFAULT_STRENGTH_THEME["range_color"])
    hidden_overlay = (0, 0, 0, 0)
    line_points: List[Tuple[int, int]] = []

    for x, match in zip(x_positions, matches):
        _draw_range_track(
            draw,
            x=x,
            full_range=match.get("all_role_range") or {},
            current_range=match.get("current_all_role_range") or {},
            y_for=y_for,
            width=all_role_width,
            base_color=range_color,
            active_color=hidden_overlay,
            scale=scale,
        )
        _draw_range_track(
            draw,
            x=x,
            full_range=match.get("role_range") or {},
            current_range=match.get("current_role_range") or {},
            y_for=y_for,
            width=role_width,
            base_color=range_color,
            active_color=hidden_overlay,
            scale=scale,
        )

        _draw_side_score_markers(
            draw,
            x=x,
            scores=match.get("team_scores") or [],
            y_for=y_for,
            track_width=role_width,
            side="left",
            fill=(92, 219, 148, 255),
            outline=(31, 90, 51, 255),
            inner_top=inner_top,
            inner_bottom=inner_bottom,
            scale=scale,
        )
        _draw_side_score_markers(
            draw,
            x=x,
            scores=match.get("enemy_scores") or [],
            y_for=y_for,
            track_width=role_width,
            side="right",
            fill=(255, 139, 128, 255),
            outline=(123, 39, 49, 255),
            inner_top=inner_top,
            inner_bottom=inner_bottom,
            scale=scale,
        )

        avg_score = float(match.get("avg_score") or 0)
        if avg_score > 0:
            point = (x, y_for(avg_score))
            line_points.append(point)

    if len(line_points) >= 2:
        draw.line(
            line_points,
            fill=tuple(theme.get("line_color") or DEFAULT_STRENGTH_THEME["line_color"]),
            width=max(3 * scale, 4),
        )

    bottom_line_y = inner_bottom + 24 * scale
    for idx, (x, match) in enumerate(zip(x_positions, matches), start=1):
        label_text = f"{idx}. {_format_match_label(match, config)}"
        label_text = _fit_text(draw, label_text, fonts["font_meta"], label_width_limit)
        label_width = _measure_text(draw, label_text, fonts["font_meta"])
        draw.text(
            (int(x - label_width / 2), bottom_line_y),
            label_text,
            font=fonts["font_meta"],
            fill=(197, 207, 223, 255),
        )
        date_text = _format_match_date(int(match.get("begin_ts") or 0))
        date_width = _measure_text(draw, date_text, fonts["font_meta"])
        draw.text(
            (int(x - date_width / 2), bottom_line_y + 22 * scale),
            date_text,
            font=fonts["font_meta"],
            fill=(132, 151, 176, 255),
        )


def _draw_footer(draw: Any, *, fonts: Dict[str, Any], scale: int, theme: Dict[str, Any]) -> None:
    x1 = 72 * scale
    y1 = 898 * scale
    range_legend_color = tuple(theme.get("range_color") or DEFAULT_STRENGTH_THEME["range_color"])
    legend_items = [
        ("\u804c\u8d23\u533a\u95f4", range_legend_color),
        ("\u5168\u804c\u8d23\u533a\u95f4", range_legend_color),
        ("\u961f\u53cb\u804c\u8d23\u5206", (92, 219, 148, 255)),
        ("\u5bf9\u624b\u804c\u8d23\u5206", (255, 139, 128, 255)),
        ("\u5e73\u5747\u5f3a\u5ea6\u7ebf", tuple(theme.get("line_color") or DEFAULT_STRENGTH_THEME["line_color"])),
    ]
    draw.text((x1, y1), "\u56fe\u4f8b", font=fonts["font_panel_title"], fill=(236, 243, 251, 255))
    cur_x = x1 + 64 * scale
    for label, color in legend_items:
        draw.rectangle(
            (cur_x, y1 + 8 * scale, cur_x + 18 * scale, y1 + 18 * scale),
            fill=color,
        )
        draw.text(
            (cur_x + 28 * scale, y1 + 1 * scale),
            label,
            font=fonts["font_meta"],
            fill=(173, 186, 205, 255),
        )
        cur_x += _measure_text(draw, label, fonts["font_meta"]) + 64 * scale


def _draw_range_track(
    draw: Any,
    *,
    x: int,
    full_range: Dict[str, Any],
    current_range: Dict[str, Any],
    y_for: Any,
    width: int,
    base_color: Tuple[int, int, int, int],
    active_color: Tuple[int, int, int, int],
    scale: int,
) -> None:
    full_min = int(full_range.get("min") or 0)
    full_max = int(full_range.get("max") or 0)
    if full_min <= 0 or full_max <= 0 or full_max < full_min:
        return
    top = y_for(full_max)
    bottom = y_for(full_min)
    radius = max(scale, min(width // 12, 2 * scale))
    draw.rounded_rectangle(
        (x - width // 2, top, x + width // 2, bottom),
        radius=radius,
        fill=base_color,
    )

    current_min = int(current_range.get("min") or 0)
    current_max = int(current_range.get("max") or 0)
    if current_min <= 0 or current_max <= 0 or current_max < current_min:
        return
    overlap_min = max(full_min, current_min)
    overlap_max = min(full_max, current_max)
    if overlap_max < overlap_min:
        return
    active_top = y_for(overlap_max)
    active_bottom = y_for(overlap_min)
    if len(active_color) >= 4 and int(active_color[3]) <= 0:
        return
    inset = max(scale, 1)
    draw.rounded_rectangle(
        (x - width // 2 + inset, active_top, x + width // 2 - inset, active_bottom),
        radius=max(radius - inset, 1),
        fill=active_color,
    )


def _draw_match_backdrops(
    canvas: Any,
    *,
    draw: Any,
    matches: Sequence[Dict[str, Any]],
    config: Dict[str, Any],
    x_positions: Sequence[int],
    inner_left: int,
    inner_right: int,
    inner_top: int,
    inner_bottom: int,
    scale: int,
) -> None:
    if not matches or not x_positions:
        return
    for idx, (x, match) in enumerate(zip(x_positions, matches)):
        if idx == 0:
            left = inner_left
        else:
            left = int((x_positions[idx - 1] + x) / 2)
        if idx == len(x_positions) - 1:
            right = inner_right
        else:
            right = int((x + x_positions[idx + 1]) / 2)
        left += 4 * scale
        right -= 4 * scale
        width = right - left
        height = inner_bottom - inner_top
        if width <= 18 * scale or height <= 24 * scale:
            continue
        backdrop = _load_map_backdrop(
            config=config,
            map_guid=match.get("map_guid"),
            size=(width, height),
        )
        if backdrop is not None:
            canvas.alpha_composite(backdrop, (left, inner_top))
        _draw_match_result_bars(
            draw,
            left=left,
            right=right,
            top=inner_top,
            bottom=inner_bottom,
            result=match.get("result"),
            scale=scale,
        )


def _draw_side_score_markers(
    draw: Any,
    *,
    x: int,
    scores: Sequence[Any],
    y_for: Any,
    track_width: int,
    side: str,
    fill: Tuple[int, int, int, int],
    outline: Tuple[int, int, int, int],
    inner_top: int,
    inner_bottom: int,
    scale: int,
) -> None:
    grouped_scores = _group_scores(scores)
    if not grouped_scores:
        return
    edge_pad = 0
    marker_width = max(2 * scale, 4)
    marker_gap = max(scale // 2, 1)
    marker_half_height = max(5 * scale, 6)
    for score_num, count in grouped_scores:
        y = y_for(score_num)
        y1 = max(inner_top, y - marker_half_height)
        y2 = min(inner_bottom, y + marker_half_height)
        if y2 <= y1:
            continue
        for idx in range(count):
            if side == "left":
                x1 = x - track_width // 2 + edge_pad + idx * (marker_width + marker_gap)
                x2 = x1 + marker_width
            else:
                x2 = x + track_width // 2 - edge_pad - idx * (marker_width + marker_gap)
                x1 = x2 - marker_width
            if x2 <= x1:
                continue
            draw.rectangle(
                (x1, y1, x2, y2),
                fill=fill,
                outline=outline,
                width=max(1, scale),
            )


def _load_map_backdrop(
    *,
    config: Dict[str, Any],
    map_guid: Any,
    size: Tuple[int, int],
) -> Any:
    from PIL import Image, ImageEnhance, ImageOps

    width, height = size
    if width <= 0 or height <= 0:
        return None
    icon_url = _map_icon_url(config, map_guid)
    if not icon_url:
        return None
    local_path = get_cached_asset_path(icon_url, "maps")
    if not local_path or not Path(local_path).exists():
        return None
    try:
        image = Image.open(local_path).convert("RGBA")
    except Exception:
        return None

    try:
        image = ImageOps.fit(image, (width, height), method=Image.LANCZOS, centering=(0.5, 0.5))
    except Exception:
        try:
            image = image.resize((width, height), Image.LANCZOS)
        except Exception:
            return None
    image = ImageEnhance.Brightness(image).enhance(0.9)
    image = ImageEnhance.Color(image).enhance(0.96)
    alpha = image.getchannel("A").point(lambda value: int(value * 0.5))
    image.putalpha(alpha)
    shade = Image.new("RGBA", image.size, (11, 17, 28, 18))
    image.alpha_composite(shade)
    return image


def _draw_match_result_bars(
    draw: Any,
    *,
    left: int,
    right: int,
    top: int,
    bottom: int,
    result: Any,
    scale: int,
) -> None:
    if right <= left or bottom <= top:
        return
    fill = _result_strip_color(result)
    strip_height = max(3 * scale, 4)
    draw.rectangle((left, top, right, min(bottom, top + strip_height)), fill=fill)
    draw.rectangle((left, max(top, bottom - strip_height), right, bottom), fill=fill)


def _collect_chart_scores(matches: Sequence[Dict[str, Any]]) -> List[int]:
    values: List[int] = []
    for match in matches:
        try:
            avg_score = int(float(match.get("avg_score") or 0))
        except (TypeError, ValueError):
            avg_score = 0
        if avg_score > 0:
            values.append(avg_score)

        for range_key in (
            "role_range",
            "all_role_range",
            "current_role_range",
            "current_all_role_range",
        ):
            score_range = match.get(range_key) if isinstance(match.get(range_key), dict) else {}
            for bound_key in ("min", "max"):
                try:
                    score = int(score_range.get(bound_key) or 0)
                except (TypeError, ValueError):
                    score = 0
                if score > 0:
                    values.append(score)

        for score in list(match.get("team_scores") or []) + list(match.get("enemy_scores") or []):
            try:
                score_num = int(float(score))
            except (TypeError, ValueError):
                continue
            if score_num > 0:
                values.append(score_num)
    return values


def _group_scores(scores: Sequence[Any]) -> List[Tuple[int, int]]:
    counts: Dict[int, int] = {}
    for score in scores or []:
        try:
            score_num = int(float(score))
        except (TypeError, ValueError):
            continue
        if score_num <= 0:
            continue
        counts[score_num] = counts.get(score_num, 0) + 1
    return [(score_num, counts[score_num]) for score_num in sorted(counts.keys())]


def _load_rank_flat_icon(score: float, *, size: Tuple[int, int]) -> Any:
    from PIL import Image

    level = _rank_icon_level_from_score(score)
    if level <= 0:
        return None
    candidates = [
        RESOURCE_DIR / "rank_flat" / f"{level}_pure.png",
        RESOURCE_DIR / "rank_flat" / f"f{level}_pure.png",
        RESOURCE_DIR / "rank_flat" / f"{level}.png",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            return Image.open(path).convert("RGBA").resize(size, Image.LANCZOS)
        except Exception:
            continue
    return None


def _rank_icon_level_from_score(score: float) -> int:
    try:
        score_num = int(float(score))
    except (TypeError, ValueError):
        return 0
    if score_num <= 0:
        return 0
    if score_num < 1500:
        return 1
    if score_num < 2000:
        return 2
    if score_num < 2500:
        return 3
    if score_num < 3000:
        return 4
    if score_num < 3500:
        return 5
    if score_num < 4000:
        return 6
    if score_num < 4500:
        return 7
    return 8


def _score_to_rank_cn(score: Any) -> str:
    return _rank_text_cn(score_to_rank(score))


def _rank_text_cn(rank_text: Any) -> str:
    raw = str(rank_text or "").strip()
    if not raw:
        return RANK_LABELS_CN["Unranked"]
    if raw in RANK_LABELS_CN:
        return RANK_LABELS_CN[raw]
    for key, label in RANK_LABELS_CN.items():
        prefix = f"{key} "
        if raw.startswith(prefix):
            return f"{label}{raw[len(prefix):].strip()}"
    return raw


def _format_match_label(match: Dict[str, Any], config: Dict[str, Any]) -> str:
    map_name = _map_name(config, match.get("map_guid"))
    try:
        result_key = int(match.get("result") or 0)
    except (TypeError, ValueError):
        result_key = 0
    result_text = RESULT_LABELS.get(result_key, RESULT_LABELS[0])
    return f"{map_name}\uff08{result_text}\uff09"


def _map_icon_url(config: Dict[str, Any], map_guid: Any) -> str:
    item = _map_item(config, map_guid)
    return str(item.get("icon") or "").strip() if item else ""


def _map_name(config: Dict[str, Any], map_guid: Any) -> str:
    item = _map_item(config, map_guid)
    if not item:
        return str(map_guid or "").strip() or "\u672a\u77e5\u5730\u56fe"
    for key in ("name", "displayName", "ename"):
        text = _normalize_display_text(item.get(key))
        if text:
            return text
    return str(map_guid or "").strip() or "\u672a\u77e5\u5730\u56fe"


def _map_item(config: Dict[str, Any], map_guid: Any) -> Dict[str, Any]:
    target = str(map_guid or "").strip()
    for item in config.get("mapList", []) or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("guid") or "").strip() != target:
            continue
        return item
    return {}


def _normalize_display_text(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    repaired = _repair_mojibake(raw)
    return repaired or raw


def _repair_mojibake(text: str) -> str:
    best = text
    best_quality = _text_quality(text)
    for encoding in ("gbk", "cp936", "gb18030"):
        try:
            candidate = text.encode(encoding).decode("utf-8")
        except Exception:
            continue
        if not candidate or candidate == best:
            continue
        candidate_quality = _text_quality(candidate)
        if candidate_quality > best_quality:
            best = candidate
            best_quality = candidate_quality
            continue
        if _cjk_ratio(text) >= 0.8 and _cjk_ratio(candidate) >= 0.8 and len(candidate) + 1 < len(best):
            best = candidate
            best_quality = candidate_quality
    return best


def _text_quality(text: str) -> int:
    score = 0
    for char in text:
        if "\u4e00" <= char <= "\u9fff":
            score += 3
        elif char.isascii() and (char.isalnum() or char in " -_#/.()"):
            score += 1
        elif char in ("\uff08", "\uff09", "\u00b7"):
            score += 1
        elif ord(char) < 32:
            score -= 2
    for token in (
        "\u5927\u9053",
        "\u8857",
        "\u795e\u6bbf",
        "\u5bfa",
        "\u5854",
        "\u57ce",
        "\u6751",
        "\u5cad",
        "\u533a",
        "\u7ad9",
        "\u5c71",
        "\u5de5\u4e1a",
        "\u6e2f",
        "\u4fee\u9053\u9662",
        "\u673a\u573a",
        "\u76d1\u6d4b\u7ad9",
        "\u738b",
        "\u7387",
    ):
        if token in text:
            score += 3
    return score


def _cjk_ratio(text: str) -> float:
    if not text:
        return 0.0
    cjk_count = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    return cjk_count / max(len(text), 1)


def _load_fonts(scale: int) -> Dict[str, Any]:
    return {
        "font_title": _font_resource("bignoodletoooblique.ttf", 32 * scale, fallback="BigNoodleToo.ttf"),
        "font_id_suffix": _font_resource("BigNoodleToo.ttf", 18 * scale, fallback="en2.ttf"),
        "font_panel_title": _font_chinese(18 * scale, bold=True),
        "font_summary_rank": _font_chinese(24 * scale, bold=True),
        "font_summary_label": _font_chinese(12 * scale, bold=True),
        "font_sub": _font_chinese(14 * scale),
        "font_meta": _font_chinese(11 * scale),
        "font_axis": _font_chinese(12 * scale),
        "font_mono": _font_resource("BigNoodleToo.ttf", 22 * scale, fallback="en.ttf"),
    }


def _font_resource(name: str, size: int, *, fallback: str | None = None) -> Any:
    from PIL import ImageFont

    candidates = [RESOURCE_DIR / name]
    if fallback:
        candidates.append(RESOURCE_DIR / fallback)
    candidates.extend(
        [
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/msyh.ttc"),
            Path("C:/Windows/Fonts/simhei.ttf"),
        ]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(str(path), size)
        except Exception:
            continue
    return ImageFont.load_default()


def _font_chinese(size: int, *, bold: bool = False) -> Any:
    from PIL import ImageFont

    candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        RESOURCE_DIR / "GrotaRoundedExtraBold.otf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(str(path), size)
        except Exception:
            continue
    return ImageFont.load_default()


def _measure_text(draw: Any, text: str, font: Any) -> int:
    try:
        return int(draw.textlength(str(text or ""), font=font))
    except Exception:
        box = draw.textbbox((0, 0), str(text or ""), font=font)
        return int(box[2] - box[0])


def _format_match_date(begin_ts: int) -> str:
    if begin_ts <= 0:
        return "--/--"
    try:
        return dt.datetime.fromtimestamp(begin_ts / 1000).strftime("%m/%d")
    except Exception:
        return "--/--"


def _fit_text(draw: Any, text: str, font: Any, max_width: int) -> str:
    if max_width <= 0:
        return ""
    content = str(text or "")
    if _measure_text(draw, content, font) <= max_width:
        return content
    suffix = "..."
    trimmed = content
    while trimmed and _measure_text(draw, trimmed + suffix, font) > max_width:
        trimmed = trimmed[:-1]
    return (trimmed + suffix) if trimmed else suffix


def _result_color(result: Any) -> Tuple[int, int, int, int]:
    try:
        result_num = int(result or 0)
    except (TypeError, ValueError):
        result_num = 0
    if result_num == 1:
        return (246, 208, 75, 255)
    if result_num == -1:
        return (255, 92, 92, 255)
    return (181, 190, 204, 255)


def _result_strip_color(result: Any) -> Tuple[int, int, int, int]:
    try:
        result_num = int(result or 0)
    except (TypeError, ValueError):
        result_num = 0
    if result_num == 1:
        return (92, 219, 148, 220)
    if result_num == -1:
        return (255, 92, 92, 220)
    return (160, 170, 185, 220)


def _open_avatar(
    avatar_bytes: Optional[bytes],
    *,
    size: int,
    ring_color: Tuple[int, int, int, int],
) -> Any:
    from PIL import Image, ImageDraw, ImageOps

    if not avatar_bytes:
        return None
    try:
        avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA")
    except Exception:
        return None
    avatar = ImageOps.fit(avatar, (size, size), method=Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    avatar.putalpha(mask)
    ring = Image.new("RGBA", (size + 12, size + 12), (0, 0, 0, 0))
    ring_draw = ImageDraw.Draw(ring)
    ring_draw.ellipse((0, 0, size + 12, size + 12), fill=ring_color)
    ring_draw.ellipse((6, 6, size + 6, size + 6), fill=(0, 0, 0, 0))
    ring.paste(avatar, (6, 6), avatar)
    return ring
