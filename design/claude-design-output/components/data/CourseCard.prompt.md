Course/section card — the primary unit in course search and requirement lists. Code in mono, title in Source Serif 4, breadth as spectrum chips, status with icon+label. `compact` gives the dense row for lists; `draggable` for the plan board.

```jsx
<CourseCard code="POL208H1" title="Introduction to International Relations" credit={0.5}
  breadth={['BR3']} fall winter status="available" onAdd={add} onDetails={open} />
<CourseCard compact code="MAT137Y1" title="Calculus with Proofs" credit={1.0} status="planned" />
```
