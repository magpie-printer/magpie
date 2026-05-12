# Plated Parts

STL files for all printed parts of the Magpie printer.

## Print Settings

Use the VORON STANDARD profile for all parts:

- Layer height: 0.2mm
- Extrusion width: 0.4mm (forced)
- Infill: 40%
- Infill type: Grid, gyroid, honeycomb, triangle, or cubic
- Wall count: 4
- Solid top/bottom layers: 5
- Supports: NONE

These settings are specified in the build guide.

## Materials

Acceptable: ASA, ABS, PETG, PCTG, PLA

Don't enclose a PLA printer. If you want an enclosed build, use ABS, PETG, or ASA instead.

## Print Order

Print in this order:

### 1. Frame

`top_frame_corner_pieces.stl`  
`top_frame_connecting_pieces.stl`  
`Bottom_frame_corner_pieces.stl`  
`Bottom_frame_connecting_pieces.stl`

The frame parts are printed first. They form the main skeleton of the printer and take the longest to print.

### 2. Motion System

`X&Y_Motion_Parts.stl`  
`z_axis_parts.stl`

Print after the frame is done. The motion parts need to be accurate, so make sure there are no layer shifts.

### 3. Toolhead

Choose one based on your extruder:

`Toolhead/toolhead_pieces_Sherpa_mini.stl` — For Sherpa Mini v2  
`Toolhead/toolhead_pieces_Orbiter2.stl` — For Orbiter 2  

You can also use P1P or X1 hotends with the right adapter.

### 4. Enclosure (Optional)

`Enclosure/enclosure_lid_parts.stl`  
`Enclosure/Door_parts.stl`

Optional. The enclosure improves thermal control and reduces noise, but the printer works without it.

### 5. Precision Shim

`Printable Precision Shim/`

Print these only if you need them for bed leveling during final assembly.

## Timing

Total print time is 200-350 hours depending on whether you print the enclosure. This assumes continuous printing. If you have multiple printers, you can speed this up by printing parts in parallel.

## References

- Assembly instructions: `../Build Guide/build_guide.pdf`
- CAD source files: `../cad/` (FreeCAD format, can be edited and re-exported)
- BOM (hardware, electronics, fasteners): https://docs.google.com/spreadsheets/d/1rcG37SRJA-JKYnLYInnxDPbj7JWwB8L_99AdPJc4EQ8/edit?usp=sharing
- Questions? Ask in the [Discord](https://discord.gg/zkxYRuTDAA)