Renders parsed prerequisite AND/OR logic as a nested tree; met parts show success, unmet tertiary, blocking danger.

```jsx
<PrereqTree node={{ type:'group', op:'OR', children:[
  { type:'credits', text:'4.0 credits', met:true },
  { type:'course', code:'POL101Y1', met:false },
]}} />
```
