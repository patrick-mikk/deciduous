# Assets Directory

This directory contains visual assets for the Course Dashboard application.

## Directory Structure

```
assets/
├── icons/          # SVG icons for UI elements
├── images/         # Images and logos
├── fonts/          # Custom fonts (if any)
└── colors/         # Color palette definitions
```

## Icon Requirements

The following icons are referenced in the application:

- `overview.svg` - Academic Overview tab icon
- `courses.svg` - Course Management tab icon
- `transcript.svg` - Transcript tab icon
- `planning.svg` - Degree Planning tab icon
- `analytics.svg` - Analytics & Reports tab icon

## Recommended Icon Style

- **Format**: SVG (scalable)
- **Size**: 16x16px base size
- **Style**: Line icons with 2px stroke
- **Colors**: Use Constants.primaryBlue or Constants.textSecondary
- **Theme**: Academic/education focused

## Sample Icon Implementation

```svg
<!-- overview.svg -->
<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="1" y="1" width="6" height="6" stroke="#002a5c" stroke-width="2" fill="none"/>
  <rect x="9" y="1" width="6" height="6" stroke="#002a5c" stroke-width="2" fill="none"/>
  <rect x="1" y="9" width="6" height="6" stroke="#002a5c" stroke-width="2" fill="none"/>
  <rect x="9" y="9" width="6" height="6" stroke="#002a5c" stroke-width="2" fill="none"/>
</svg>
```

## Usage in QML

Icons are referenced in components like this:

```qml
CourseTabButton {
    text: "Academic Overview"
    iconSource: "assets/icons/overview.svg"
}
```

## Color Integration

Icons should use colors from the Constants.qml file:
- Primary: `#002a5c` (Constants.primaryBlue)
- Secondary: `#495057` (Constants.textSecondary)
- Accent: `#007bff` (Constants.lightBlue)