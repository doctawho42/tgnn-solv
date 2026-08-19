#!/usr/bin/env python
"""Generate RDKit molecule assets for the seminar deck."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from rdkit import Chem
from rdkit.Chem import AllChem, Draw, rdDepictor


OUT = Path(__file__).resolve().parent / "figures" / "molecules"
OUT.mkdir(parents=True, exist_ok=True)

BLUE = (37, 99, 235)
ORANGE = (245, 158, 11)
GREEN = (16, 185, 129)
SLATE = (15, 23, 42)
MUTED = (100, 116, 139)
BORDER = (203, 213, 225)
PAPER = (255, 255, 255)
SOFT = (248, 250, 252)

MOLECULES = {
    "paracetamol": ("Парацетамол", "CC(=O)Nc1ccc(O)cc1"),
    "ethanol": ("Этанол", "CCO"),
    "water": ("Вода", "O"),
    "benzene": ("Бензол", "c1ccccc1"),
    "methanol": ("Метанол", "CO"),
    "acetone": ("Ацетон", "CC(=O)C"),
    "dmso": ("ДМСО", "CS(=O)C"),
    "dmf": ("ДМФА", "CN(C)C=O"),
}


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT_BOLD = _font(34, bold=True)
FONT = _font(25)
FONT_SMALL = _font(20)
FONT_NODE = _font(21, bold=True)


def mol_from_smiles(smiles: str) -> Chem.Mol:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    rdDepictor.Compute2DCoords(mol)
    return mol


def draw_molecule_card(key: str, label: str, smiles: str, size: tuple[int, int] = (1080, 690)) -> None:
    mol = mol_from_smiles(smiles)
    w, h = size
    img = Image.new("RGB", size, SOFT)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([8, 8, w - 8, h - 8], radius=34, fill=PAPER, outline=BORDER, width=2)
    d.text((34, 28), label, fill=SLATE, font=FONT_BOLD)
    d.text((34, 64), smiles, fill=MUTED, font=FONT_SMALL)
    mol_img = Draw.MolToImage(mol, size=(w - 70, h - 126), kekulize=True)
    img.paste(mol_img, (35, 106))
    img.save(OUT / f"{key}.png", dpi=(300, 300))


def draw_plain_molecule(key: str, smiles: str, size: tuple[int, int] = (1440, 840)) -> None:
    """Write a high-resolution molecule-only depiction for dense slides."""
    mol = mol_from_smiles(smiles)
    if key == "water":
        mol = Chem.AddHs(mol)
        rdDepictor.Compute2DCoords(mol)
    img = Draw.MolToImage(mol, size=size, kekulize=True)
    img.save(OUT / f"{key}_plain.png", dpi=(300, 300))


def get_2d_positions(mol: Chem.Mol, box: tuple[int, int, int, int]) -> dict[int, tuple[float, float]]:
    conf = mol.GetConformer()
    xs, ys = [], []
    for atom in mol.GetAtoms():
        p = conf.GetAtomPosition(atom.GetIdx())
        xs.append(p.x)
        ys.append(p.y)
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    left, top, right, bottom = box
    span_x = max(max_x - min_x, 1e-6)
    span_y = max(max_y - min_y, 1e-6)
    scale = min((right - left) / span_x, (bottom - top) / span_y) * 0.84
    cx = (left + right) / 2
    cy = (top + bottom) / 2
    mol_cx = (min_x + max_x) / 2
    mol_cy = (min_y + max_y) / 2
    coords = {}
    for atom in mol.GetAtoms():
        p = conf.GetAtomPosition(atom.GetIdx())
        x = cx + (p.x - mol_cx) * scale
        y = cy - (p.y - mol_cy) * scale
        coords[atom.GetIdx()] = (x, y)
    return coords


def draw_graph_card(key: str, label: str, smiles: str, size: tuple[int, int] = (1080, 690)) -> None:
    mol = mol_from_smiles(smiles)
    w, h = size
    img = Image.new("RGB", size, SOFT)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([8, 8, w - 8, h - 8], radius=34, fill=PAPER, outline=BORDER, width=2)
    d.text((34, 28), f"{label}: молекулярный граф", fill=SLATE, font=FONT_BOLD)
    d.text((34, 64), "узлы = атомы, рёбра = связи; координаты из 2D-структуры RDKit", fill=MUTED, font=FONT_SMALL)
    coords = get_2d_positions(mol, (70, 120, w - 70, h - 45))

    for bond in mol.GetBonds():
        a = bond.GetBeginAtomIdx()
        b = bond.GetEndAtomIdx()
        d.line([coords[a], coords[b]], fill=(71, 85, 105), width=5)

    for atom in mol.GetAtoms():
        idx = atom.GetIdx()
        x, y = coords[idx]
        symbol = atom.GetSymbol()
        fill = (219, 234, 254) if symbol == "C" else (254, 243, 199) if symbol == "O" else (237, 233, 254)
        outline = BLUE if symbol == "C" else ORANGE if symbol == "O" else GREEN
        r = 30
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill, outline=outline, width=4)
        text = f"{symbol}{idx}"
        bbox = d.textbbox((0, 0), text, font=FONT_NODE)
        d.text((x - (bbox[2] - bbox[0]) / 2, y - (bbox[3] - bbox[1]) / 2 - 1), text, fill=SLATE, font=FONT_NODE)

    img.save(OUT / f"{key}_graph.png", dpi=(300, 300))


def draw_pair_strip() -> None:
    left = Image.open(OUT / "paracetamol.png").resize((560, 358))
    right = Image.open(OUT / "ethanol.png").resize((420, 358))
    w, h = 1140, 420
    img = Image.new("RGB", (w, h), SOFT)
    img.paste(left, (24, 32))
    img.paste(right, (696, 32))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([590, 168, 684, 252], radius=42, fill=(219, 234, 254), outline=(147, 197, 253), width=2)
    d.text((610, 188), "pair", fill=BLUE, font=FONT_BOLD)
    d.line([(585, 210), (540, 210)], fill=BLUE, width=4)
    d.line([(685, 210), (730, 210)], fill=BLUE, width=4)
    img.save(OUT / "pair_paracetamol_ethanol.png", dpi=(300, 300))


def draw_cross_attention_pair() -> None:
    solute = mol_from_smiles(MOLECULES["paracetamol"][1])
    solvent = mol_from_smiles(MOLECULES["dmso"][1])
    solute_img = Draw.MolToImage(solute, size=(360, 250), kekulize=True)
    solvent_img = Draw.MolToImage(solvent, size=(280, 250), kekulize=True)

    w, h = 1080, 430
    img = Image.new("RGB", (w, h), SOFT)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([12, 12, w - 12, h - 12], radius=34, fill=PAPER, outline=BORDER, width=2)
    d.text((34, 28), "Карта внимания для пары молекул", fill=SLATE, font=FONT_BOLD)
    d.text((34, 64), "Атомы парацетамола смотрят на атомы ДМСО; агрегированное состояние идёт в NRTL.", fill=MUTED, font=FONT_SMALL)

    left_box = (42, 118, 410, 360)
    right_box = (758, 118, 1038, 360)
    d.rounded_rectangle(left_box, radius=26, fill=(248, 250, 252), outline=(219, 234, 254), width=2)
    d.rounded_rectangle(right_box, radius=26, fill=(248, 250, 252), outline=(254, 243, 199), width=2)
    img.paste(solute_img, (left_box[0] + 8, left_box[1] + 2))
    img.paste(solvent_img, (right_box[0], right_box[1] + 2))
    d.text((left_box[0] + 18, left_box[3] - 32), "граф вещества", fill=BLUE, font=FONT_SMALL)
    d.text((right_box[0] + 18, right_box[3] - 32), "граф растворителя", fill=ORANGE, font=FONT_SMALL)

    matrix_left, matrix_top = 505, 142
    cell = 22
    values = [
        [0.05, 0.10, 0.20, 0.35, 0.80],
        [0.08, 0.15, 0.45, 0.55, 0.30],
        [0.20, 0.22, 0.78, 0.28, 0.18],
        [0.72, 0.36, 0.12, 0.18, 0.08],
        [0.50, 0.64, 0.30, 0.12, 0.05],
    ]
    d.rounded_rectangle([470, 116, 704, 358], radius=24, fill=(248, 250, 252), outline=BORDER, width=2)
    d.text((500, 124), "карта внимания", fill=SLATE, font=FONT_SMALL)
    for r, row in enumerate(values):
        for c, val in enumerate(row):
            blue = int(235 - val * 120)
            color = (blue, int(245 - val * 120), 255)
            x0 = matrix_left + c * (cell + 5)
            y0 = matrix_top + r * (cell + 5)
            d.rounded_rectangle([x0, y0, x0 + cell, y0 + cell], radius=5, fill=color, outline=(219, 234, 254), width=1)
    d.text((500, 308), "QK^T / sqrt(d)", fill=MUTED, font=FONT_SMALL)
    d.line([(410, 240), (470, 240)], fill=BLUE, width=5)
    d.line([(704, 240), (758, 240)], fill=ORANGE, width=5)
    img.save(OUT / "cross_attention_pair.png", dpi=(300, 300))


def draw_solvent_grid() -> None:
    keys = ["ethanol", "methanol", "acetone", "dmso", "dmf", "water"]
    labels = ["Ethanol", "Methanol", "Acetone", "DMSO", "DMF", "Water"]
    thumbs = []
    for key in keys:
        img = Image.open(OUT / f"{key}.png").resize((300, 192))
        thumbs.append(img)
    w, h = 960, 500
    img = Image.new("RGB", (w, h), SOFT)
    d = ImageDraw.Draw(img)
    d.text((32, 24), "Примеры частых растворителей в корпусе", fill=SLATE, font=FONT_BOLD)
    for i, thumb in enumerate(thumbs):
        row, col = divmod(i, 3)
        x = 30 + col * 310
        y = 74 + row * 205
        img.paste(thumb, (x, y))
        d.text((x + 22, y + 152), labels[i], fill=SLATE, font=FONT)
    img.save(OUT / "solvent_grid.png", dpi=(300, 300))


def classify_bond(atom_a: Chem.Atom, atom_b: Chem.Atom) -> str:
    symbols = {atom_a.GetSymbol(), atom_b.GetSymbol()}
    if symbols & {"O", "N", "F"}:
        return "polar"
    return "disp"


def draw_timp_highlight() -> None:
    key, (label, smiles) = "paracetamol", MOLECULES["paracetamol"]
    mol = mol_from_smiles(smiles)
    w, h = 860, 500
    img = Image.new("RGB", (w, h), SOFT)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([8, 8, w - 8, h - 8], radius=36, fill=PAPER, outline=BORDER, width=2)
    d.text((36, 28), "TIMP: два канала на графе", fill=SLATE, font=FONT_BOLD)
    d.text((36, 64), "синий = дисперсия, оранжевый = полярность / H-связи", fill=MUTED, font=FONT_SMALL)
    coords = get_2d_positions(mol, (90, 120, w - 90, h - 68))

    for bond in mol.GetBonds():
        a_idx, b_idx = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        channel = classify_bond(mol.GetAtomWithIdx(a_idx), mol.GetAtomWithIdx(b_idx))
        color = ORANGE if channel == "polar" else BLUE
        d.line([coords[a_idx], coords[b_idx]], fill=color, width=8)

    for atom in mol.GetAtoms():
        idx = atom.GetIdx()
        x, y = coords[idx]
        symbol = atom.GetSymbol()
        fill = (219, 234, 254) if symbol == "C" else (254, 243, 199) if symbol == "O" else (237, 233, 254)
        outline = BLUE if symbol == "C" else ORANGE if symbol == "O" else GREEN
        r = 20
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill, outline=outline, width=4)
        bbox = d.textbbox((0, 0), symbol, font=FONT_NODE)
        d.text((x - (bbox[2] - bbox[0]) / 2, y - (bbox[3] - bbox[1]) / 2 - 1), symbol, fill=SLATE, font=FONT_NODE)

    d.rounded_rectangle([36, h - 62, 250, h - 26], radius=18, fill=(219, 234, 254), outline=(147, 197, 253), width=2)
    d.text((74, h - 55), "дисперсия", fill=BLUE, font=FONT)
    d.rounded_rectangle([284, h - 62, 500, h - 26], radius=18, fill=(254, 243, 199), outline=(251, 191, 36), width=2)
    d.text((324, h - 55), "полярность", fill=ORANGE, font=FONT)
    img.save(OUT / "timp_paracetamol_channels.png", dpi=(300, 300))


def main() -> None:
    for key, (label, smiles) in MOLECULES.items():
        draw_molecule_card(key, label, smiles)
        draw_plain_molecule(key, smiles)
        if key in {"paracetamol", "ethanol", "dmso", "water"}:
            draw_graph_card(key, label, smiles)
    draw_pair_strip()
    draw_cross_attention_pair()
    draw_solvent_grid()
    draw_timp_highlight()


if __name__ == "__main__":
    main()
