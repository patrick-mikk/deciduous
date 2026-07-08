Live sections grouped by teach method (LEC/TUT/PRA); one selection per method feeds the timetable. Times render from minutes-since-midnight; each row shows a SeatMeter.

```jsx
<SectionList sections={course.sections} selected={sel} onSelect={(method,name)=>pick(method,name)} />
```
