# Phase 2C: Enhanced Layout & Native PyQt6 Optimization Plan

## 🎯 **Strategic Objectives**

Transform the UofT Course Dashboard into a streamlined, professionally designed application that leverages native PyQt6 capabilities while centralizing features for optimal user experience.

### **Core Goals**
1. **Centralize Features**: Reduce cognitive load by grouping related functionality
2. **Native Styling**: Embrace PyQt6's built-in aesthetics for professional appearance
3. **Compact Layouts**: Optimize screen real estate with efficient widget arrangements
4. **Enhanced UX**: Improve workflow efficiency through better feature organization

---

## 📋 **Current State Analysis**

### **Existing Tab Structure (6 tabs - dispersed)**
- Course Search → Academic Calendar lookups
- Transcript → Completed course management
- Planning → Future course planning
- Requirements → Degree progress tracking
- GPA Dashboard → Grade analytics
- Analytics → Advanced data visualization

### **Current Issues**
- ❌ **Feature Fragmentation**: Related functions scattered across multiple tabs
- ❌ **Custom CSS Dependency**: Non-native styling that doesn't integrate well with system themes
- ❌ **Inefficient Layouts**: Underutilized screen space and poor information density
- ❌ **Navigation Overhead**: Users must switch between many tabs for common workflows

---

## 🚀 **Proposed Enhanced Layout**

### **New Tab Structure (4 tabs - centralized)**

#### **1. Academic Overview** 📊
*Main dashboard combining status, progress, and quick actions*

**Primary Functions:**
- Academic standing summary (GPA, credits, status)
- Degree progress overview with visual indicators
- Quick course search and add functionality
- Recent activity timeline
- Upcoming deadlines and milestones

**Layout Strategy:**
- Top section: Key metrics in cards (GPA, Credits, Standing)
- Middle section: Progress bars for degree completion
- Bottom section: Recent activity and quick actions
- Right sidebar: Quick course lookup and add

#### **2. Course Management** 🔍
*Unified course search, transcript, and details management*

**Primary Functions:**
- Academic Calendar course search (selenium integration)
- Transcript management with filtering and sorting
- Detailed course information display
- Bulk operations (edit, delete, move to planning)
- Course history and status tracking

**Layout Strategy:**
- Left panel: Search interface with results table
- Right panel: Course details and actions
- Bottom panel: Transcript table with filters
- Use QSplitter for resizable sections

#### **3. Degree Planning** 🎓
*Integrated planning, requirements, and program tracking*

**Primary Functions:**
- Future course planning with drag-drop
- Degree requirements progress visualization
- Program enrollment and tracking
- Breadth requirements management
- Prerequisite validation and planning

**Layout Strategy:**
- Left panel: Requirements tree with progress indicators
- Center panel: Planning workspace with semester layout
- Right panel: Course catalog and details
- Bottom status: Requirement summary and alerts

#### **4. Analytics & Reports** 📈
*Data visualization, trends, and export functionality*

**Primary Functions:**
- GPA trends and historical analysis
- Credit distribution and completion rates
- Progress charts and milestone tracking
- Export functionality for transcripts and reports
- Advanced filtering and data views

**Layout Strategy:**
- Top section: Key performance indicators
- Main area: Charts and graphs (using Qt Charts or matplotlib)
- Bottom section: Export and reporting controls
- Tabbed sub-sections for different analytics

---

## 🎨 **Native PyQt6 Styling Strategy**

### **Migration from Custom CSS to Native Styling**

#### **Remove Custom Styling Dependencies**
```python
# REMOVE: Custom QSS files
- src/gui_qt/resources/styles.qss

# REPLACE WITH: Native Qt styling approaches
- QWidget.setStyleSheet() for minimal customization only
- QPalette for color scheme management
- QApplication.setStyle() for system integration
- Built-in widget properties and states
```

#### **Native Styling Components**

**1. Color Scheme Management**
```python
# Use QPalette for consistent theming
palette = QApplication.palette()
palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
app.setPalette(palette)
```

**2. Typography**
```python
# Use QFont with system defaults
font = QApplication.font()
font.setFamily("Segoe UI")  # System appropriate
font.setPointSize(9)
app.setFont(font)
```

**3. Widget Appearance**
```python
# Leverage built-in widget properties
button.setFlat(False)  # Use native button styling
button.setDefault(True)  # Native focus indication
frame.setFrameStyle(QFrame.Shape.StyledPanel)  # Native panel look
```

#### **Professional Appearance Guidelines**

**Button Styling:**
- Use `QPushButton` default appearance with minimal customization
- Leverage `setDefault()`, `setAutoDefault()` for proper focus
- Use `QIcon` for professional button icons

**Layout Enhancement:**
- `QGroupBox` for logical section grouping
- `QSplitter` for user-resizable sections
- `QTabWidget` with native tab styling
- `QFrame` with `StyledPanel` for content separation

**Table/List Improvements:**
- `QTableWidget` with `alternatingRowColors(True)`
- Native selection highlighting
- Built-in sorting and filtering capabilities
- Professional headers with `QHeaderView`

---

## 🏗️ **Implementation Architecture**

### **Widget Organization Strategy**

#### **1. Academic Overview Tab**
```python
class AcademicOverviewWidget(QWidget):
    """Main dashboard with status cards and quick actions"""

    def __init__(self):
        # Top section: Status cards using QGroupBox
        self.create_status_cards()  # GPA, Credits, Standing

        # Middle: Progress visualization using QProgressBar
        self.create_progress_section()

        # Bottom: Activity timeline using QListWidget
        self.create_activity_section()

        # Right sidebar: Quick actions using QVBoxLayout
        self.create_quick_actions()
```

#### **2. Course Management Tab**
```python
class CourseManagementWidget(QWidget):
    """Unified course search and transcript management"""

    def __init__(self):
        # Main splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Search panel
        self.create_search_panel()

        # Center: Results and transcript table
        self.create_course_table()

        # Right: Details panel
        self.create_details_panel()
```

#### **3. Degree Planning Tab**
```python
class DegreePlanningWidget(QWidget):
    """Requirements tracking and course planning"""

    def __init__(self):
        # Three-panel layout with QSplitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Requirements tree (QTreeWidget)
        self.create_requirements_tree()

        # Center: Planning workspace (custom widget)
        self.create_planning_workspace()

        # Right: Course catalog (QListWidget)
        self.create_course_catalog()
```

#### **4. Analytics Tab**
```python
class AnalyticsWidget(QWidget):
    """Data visualization and reporting"""

    def __init__(self):
        # Top: KPI cards
        self.create_kpi_section()

        # Main: Chart area (QChartView or matplotlib)
        self.create_chart_section()

        # Bottom: Export controls
        self.create_export_section()
```

### **Layout Management Best Practices**

#### **Use Native Layout Managers**
- `QVBoxLayout`, `QHBoxLayout` for linear arrangements
- `QGridLayout` for complex positioning
- `QFormLayout` for form-style data entry
- `QStackedLayout` for switching between views

#### **Responsive Design**
- `QSplitter` for user-adjustable sections
- `setStretchFactor()` for proportional resizing
- `setSizePolicy()` for proper widget behavior
- `setMinimumSize()` for usability constraints

#### **Professional Information Density**
- `QGroupBox` for logical content grouping
- `QScrollArea` for overflow content
- `QTabWidget` for secondary organization within tabs
- Consistent spacing using layout margins and spacing

---

## 🔄 **Migration Strategy**

### **Phase 1: Layout Restructuring**
1. Create new widget classes for each tab
2. Implement native layout managers
3. Test basic functionality within new structure

### **Phase 2: Styling Migration**
1. Remove custom QSS dependencies
2. Implement QPalette-based theming
3. Test appearance across different system themes

### **Phase 3: Feature Integration**
1. Migrate existing functionality to new tabs
2. Implement cross-tab communication
3. Add enhanced workflows and shortcuts

### **Phase 4: Polish & Optimization**
1. Fine-tune layouts and spacing
2. Add native animations and transitions
3. Optimize performance and responsiveness

---

## 📊 **Expected Benefits**

### **User Experience Improvements**
- **Reduced Cognitive Load**: 4 logical tabs vs 6 dispersed tabs
- **Improved Workflow**: Related features grouped together
- **Better Information Density**: More efficient use of screen space
- **Professional Appearance**: Native styling looks polished and consistent

### **Technical Advantages**
- **System Integration**: Native styling adapts to user preferences
- **Maintainability**: Less custom CSS to maintain
- **Performance**: Native widgets are optimized
- **Accessibility**: Built-in accessibility features work properly

### **Development Benefits**
- **Faster Iteration**: Native widgets have established patterns
- **Cross-Platform**: Better consistency across operating systems
- **Future-Proof**: Qt updates improve appearance automatically
- **Reduced Complexity**: Fewer custom styling edge cases

---

## 🎯 **Success Metrics**

### **Usability Metrics**
- Time to complete common tasks (search → add course)
- Number of tab switches required for workflows
- User satisfaction with visual appearance
- Ease of finding specific functionality

### **Technical Metrics**
- Application startup time
- Memory usage optimization
- Responsiveness during data operations
- Cross-platform appearance consistency

### **Maintenance Metrics**
- Lines of custom styling code (target: reduce by 80%)
- Number of styling-related bugs
- Time to implement new features
- Compatibility with system theme changes

This comprehensive redesign will transform the UofT Course Dashboard into a modern, efficient, and professional academic management tool that leverages the full power of PyQt6 while providing an intuitive and centralized user experience.