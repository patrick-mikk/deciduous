# Academic Calendar: Functionality and Element Locator Info

## HOME PAGE

### URL

Home Page: `https://artsci.calendar.utoronto.ca/`
Course Page: `https://artsci.calendar.utoronto.ca/course/pol208h1`

### Search

JS Path: `document.querySelector("#edit-course-title")`

```html
<input data-drupal-selector="edit-course-title" type="text" id="edit-course-title" name="course_title" value="" size="30" maxlength="128" class="form-text w3-input w3-border w3-theme-border">
```

### Submit Search
JS Path: `document.querySelector("#edit-submit-search-courses-block")`

Element:
```html
<input data-drupal-selector="edit-submit-search-courses-block" type="submit" id="edit-submit-search-courses-block" value="Apply" class="button js-form-submit form-submit w3-button w3-border w3-theme-border w3-margin-top w3-margin-bottom">
```

### Results

JS Path: `document.querySelector("#block-w3css-subtheme-views-block-search-courses-block-block-1 > div > div > div.view-content > h3 > a > h6")`

Element:
```html
<div class="view-content">
        <h3><a href="/course/POL200Y1"><h6>POL200Y1: Political Theory: Visions of the Just/Good Society</h6></a></h3>
    <div class="w3-row views-row"><div class="views-field views-field-body"><div class="field-content"><p>A selective presentation of critical encounters between philosophy and politics, dedicated to the quest for articulation and founding of the just/good society. Among the theorists examined are Plato, Aristotle, Machiavelli, Hobbes and Locke.</p></div></div></div>
  <h3><a href="/course/POL201H1"><h6>POL201H1: Politics of Development</h6></a></h3>
    <div class="w3-row views-row"><div class="views-field views-field-body"><div class="field-content"><p>This course offers an introduction to the history and politics of economic and political development, starting with the Industrial Revolution and then turning to a critical analysis of the politics of economic growth, international trade, debt, state intervention, protectionism, and neo-liberalism in the global periphery, including Africa, Asia, and Latin America.</p></div></div></div>
  <h3><a href="/course/POL205H1"><h6>POL205H1: International Relations in the Anthropocene</h6></a></h3>
    <div class="w3-row views-row"><div class="views-field views-field-body"><div class="field-content"><p>Humans have altered the planet so dramatically that some geologists have coined a new epoch: the Anthropocene. Is our study of global politics up to the challenge of human-driven environmental change? In this course, we consider multiple perspectives on IR to make sense of geopolitics on a changing planet.</p></div></div></div>
  <h3><a href="/course/POL208H1"><h6>POL208H1: Introduction to International Relations</h6></a></h3>
    <div class="w3-row views-row"><div class="views-field views-field-body"><div class="field-content"><p>This introductory course examines some key themes and issues in global politics, including interstate war, human rights, international institutions, and the evolution of the global order. </p></div></div></div>
  <h3><a href="/course/POL212H1"><h6>POL212H1: Understanding War</h6></a></h3>
    <div class="w3-row views-row"><div class="views-field views-field-body"><div class="field-content"><p>General introduction to the study of war, covering basic concepts and theories and surveying a selection of key topics and debates. Sessions revolve around a few essential readings, which must be completed before class and will serve as a basis for various in-class and in-tutorial activities including presentations, case studies, simulations, and games.</p></div></div></div>

    </div>
```

### Result URL

JS Path: `document.querySelector("#block-w3css-subtheme-views-block-search-courses-block-block-1 > div > div > div.view-content > h3 > a")`

## COURSE PAGE

### Course Title

JS Path: `document.querySelector("#block-w3css-subtheme-page-title > h1")`

Element:

```html
<section id="block-w3css-subtheme-page-title" class="w3-block w3-block-wrapper block-core block-page-title-block"> 
<a name="main-content" tabindex="-1"></a> 
<h1 class="page-title">GGR273H1: Geographic Information and Mapping II</h1> 
</section>
```

### Hours

JS Path: `document.querySelector("#block-w3css-subtheme-content > article > div > div.w3-row.field.field--name-field-hours.field--type-text.field--label-inline.clearfix > div > p")`

Element:`<p>24L/24P</p>`

### Description
JS Path: `document.querySelector("#block-w3css-subtheme-content > article > div > div.w3-row.field.field--name-body.field--type-text-with-summary.field--label-hidden.w3-bar-item.field__item")`

Element:
```html
<div class="w3-row field field--name-body field--type-text-with-summary field--label-hidden w3-bar-item field__item"><p>Builds on  <a href="/course/GGR272H1">GGR272H1</a> by providing students with practical spatial analysis methods and the underlying theory needed to understand how to approach various geographic problems using geographic information system (GIS) software and a variety of data types and sources.</p></div>
```

### Prerequisite
JS Path: `document.querySelector("#block-w3css-subtheme-content > article > div > div.w3-row.field.field--name-field-prerequisite.field--type-text-long.field--label-inline.clearfix > div")`

Element:
```html
<div class="w3-bar-item field__item"><a href="/course/GGR272H1">GGR272H1</a></div>
```

### Exclusion
JS Path: `document.querySelector("#block-w3css-subtheme-content > article > div > div.w3-row.field.field--name-field-exclusion.field--type-text-long.field--label-inline.clearfix > div")`
Element:
```html
<div class="w3-bar-item field__item"><a href="https://utsc.calendar.utoronto.ca/course/GGRB32H3">GGRB32H3</a></div>
```

### Breadth Requirements 
JS Path: `document.querySelector("#block-w3css-subtheme-content > article > div > div.w3-row.field.field--name-field-breadth-requirements.field--type-list-string.field--label-inline.clearfix > div")`

Element:
```html
<div class="field__items">
              <div class="w3-bar-item field__item">The Physical and Mathematical Universes (5)</div>
              </div>
```
