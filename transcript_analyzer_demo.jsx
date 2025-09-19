import React, { useState, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, BarChart, Bar, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const TranscriptAnalyzer = () => {
  // Sample data based on your transcript
  const [transcriptData, setTranscriptData] = useState([
    { term: 'Fall 2023', year: 2023, courseCode: 'AMS199H1', title: 'Razing the Roof', weight: 0.5, mark: 80, grade: 'A-', courseAvg: 'B' },
    { term: 'Fall 2023', year: 2023, courseCode: 'MUN101H1', title: 'Global Innovation I', weight: 0.5, mark: 81, grade: 'A-', courseAvg: 'A-' },
    { term: 'Fall 2023', year: 2023, courseCode: 'MUN195H1', title: 'Economics of Birth Death', weight: 0.5, mark: 86, grade: 'A', courseAvg: 'A-' },
    { term: 'Fall 2023', year: 2023, courseCode: 'MUN198H1', title: 'Digital Technologies', weight: 0.5, mark: 82, grade: 'A-', courseAvg: 'B+' },
    { term: 'Winter 2024', year: 2024, courseCode: 'MUN102H1', title: 'Global Innovation II', weight: 0.5, mark: 55, grade: 'D', courseAvg: 'B+' },
    { term: 'Winter 2024', year: 2024, courseCode: 'MUN105Y1', title: 'Global Problem Solving', weight: 1, mark: 85, grade: 'A', courseAvg: 'A' },
    { term: 'Winter 2024', year: 2024, courseCode: 'MUN196H1', title: 'Global Politics of Surveillance', weight: 0.5, mark: 52, grade: 'D-', courseAvg: 'B' },
    { term: 'Winter 2024', year: 2024, courseCode: 'RLG107H1', title: "It's the End of the World", weight: 0.5, mark: 77, grade: 'B+', courseAvg: 'B' },
    { term: 'Summer 2024', year: 2024, courseCode: 'ECO101H1', title: 'Principles of Microeconomics', weight: 0.5, mark: 20, grade: 'F', courseAvg: 'C' },
    { term: 'Summer 2024', year: 2024, courseCode: 'HIS103Y1', title: 'Strategy and Statecraft', weight: 1, mark: 74, grade: 'B', courseAvg: 'B' },
    { term: 'Fall 2024', year: 2024, courseCode: 'AMS310H1', title: 'US Democracy at Crossroads', weight: 0.5, mark: 76, grade: 'B', courseAvg: 'B' },
    { term: 'Fall 2024', year: 2024, courseCode: 'ECO101H1', title: 'Principles of Microeconomics', weight: 0.5, mark: 53, grade: 'D', courseAvg: 'C+' },
    { term: 'Fall 2024', year: 2024, courseCode: 'STA220H1', title: 'Practice of Statistics I', weight: 0.5, mark: 50, grade: 'D-', courseAvg: 'C+' },
    { term: 'Winter 2025', year: 2025, courseCode: 'CSC108H1', title: 'Intro to Comp Prog', weight: 0.5, mark: 19, grade: 'F', courseAvg: 'C+' },
    { term: 'Winter 2025', year: 2025, courseCode: 'GGR274H1', title: 'Comp & Data Sci', weight: 0.5, mark: 70, grade: 'B-', courseAvg: 'B' },
    { term: 'Winter 2025', year: 2025, courseCode: 'MUN200H1', title: 'Understanding Global Controversies', weight: 0.5, mark: 75, grade: 'B', courseAvg: 'B' },
    { term: 'Winter 2025', year: 2025, courseCode: 'POL214H1', title: 'Canadian Government', weight: 0.5, mark: 66, grade: 'C', courseAvg: 'B' },
    { term: 'Summer 2025', year: 2025, courseCode: 'ECO102H1', title: 'Principles of Macroeconomics', weight: 0.5, mark: 51, grade: 'D-', courseAvg: 'C+' }
  ]);

  const [activeTab, setActiveTab] = useState('dashboard');
  const [simulationCourses, setSimulationCourses] = useState([]);

  // Grade point mapping
  const GRADE_POINTS = {
    'A+': 4.0, 'A': 4.0, 'A-': 3.7,
    'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7,
    'D+': 1.3, 'D': 1.0, 'D-': 0.7,
    'F': 0.0
  };

  const EXCLUDED_GRADES = ['CR', 'NCR', 'IPR', 'LWD', 'WDR', 'AEG', 'SDF'];

  // Calculate GPA for given courses
  const calculateGPA = (courses) => {
    const validCourses = courses.filter(course => 
      course.grade && !EXCLUDED_GRADES.includes(course.grade) && GRADE_POINTS.hasOwnProperty(course.grade)
    );
    
    if (validCourses.length === 0) return 0;
    
    const totalGradePoints = validCourses.reduce((sum, course) => 
      sum + (GRADE_POINTS[course.grade] * course.weight), 0
    );
    const totalCredits = validCourses.reduce((sum, course) => sum + course.weight, 0);
    
    return totalCredits > 0 ? totalGradePoints / totalCredits : 0;
  };

  // Calculate sessional GPAs
  const sessionalGPAs = useMemo(() => {
    const termMap = new Map();
    
    transcriptData.forEach(course => {
      const termKey = `${course.term} ${course.year}`;
      if (!termMap.has(termKey)) {
        termMap.set(termKey, []);
      }
      termMap.get(termKey).push(course);
    });
    
    return Array.from(termMap.entries()).map(([term, courses]) => ({
      term,
      gpa: calculateGPA(courses),
      courses: courses.length,
      credits: courses.reduce((sum, course) => sum + course.weight, 0)
    })).sort((a, b) => {
      const [termA, yearA] = a.term.split(' ');
      const [termB, yearB] = b.term.split(' ');
      if (yearA !== yearB) return parseInt(yearA) - parseInt(yearB);
      const termOrder = { 'Fall': 1, 'Winter': 2, 'Summer': 3 };
      return termOrder[termA] - termOrder[termB];
    });
  }, [transcriptData]);

  // Calculate cumulative GPA
  const cumulativeGPA = useMemo(() => calculateGPA(transcriptData), [transcriptData]);

  // Grade distribution
  const gradeDistribution = useMemo(() => {
    const distribution = {};
    transcriptData.forEach(course => {
      if (course.grade && !EXCLUDED_GRADES.includes(course.grade)) {
        distribution[course.grade] = (distribution[course.grade] || 0) + 1;
      }
    });
    return Object.entries(distribution).map(([grade, count]) => ({ grade, count }));
  }, [transcriptData]);

  // Performance comparison to course averages
  const performanceComparison = useMemo(() => {
    const avgMap = { 'A+': 4.0, 'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7, 'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0, 'D-': 0.7, 'F': 0.0 };
    
    let aboveAverage = 0, atAverage = 0, belowAverage = 0;
    
    transcriptData.forEach(course => {
      if (course.grade && course.courseAvg && !EXCLUDED_GRADES.includes(course.grade)) {
        const studentGPA = GRADE_POINTS[course.grade];
        const courseAvgGPA = avgMap[course.courseAvg];
        
        if (studentGPA > courseAvgGPA) aboveAverage++;
        else if (studentGPA === courseAvgGPA) atAverage++;
        else belowAverage++;
      }
    });
    
    return [
      { name: 'Above Average', value: aboveAverage, color: '#22c55e' },
      { name: 'At Average', value: atAverage, color: '#eab308' },
      { name: 'Below Average', value: belowAverage, color: '#ef4444' }
    ];
  }, [transcriptData]);

  // Simulation function
  const simulateFutureGPA = (futureCourses) => {
    const allCourses = [...transcriptData, ...futureCourses];
    return calculateGPA(allCourses);
  };

  const addSimulationCourse = () => {
    setSimulationCourses([...simulationCourses, { 
      courseCode: '', 
      weight: 0.5, 
      expectedGrade: 'B',
      id: Date.now()
    }]);
  };

  const updateSimulationCourse = (id, field, value) => {
    setSimulationCourses(simulationCourses.map(course => 
      course.id === id ? { ...course, [field]: value } : course
    ));
  };

  const removeSimulationCourse = (id) => {
    setSimulationCourses(simulationCourses.filter(course => course.id !== id));
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Academic Transcript Analyzer</h1>
          <p className="text-gray-600">University of Toronto Grade Analysis & Planning Tool</p>
          
          {/* Key Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mt-6">
            <div className="bg-blue-50 p-4 rounded-lg">
              <h3 className="text-sm font-medium text-blue-600">Cumulative GPA</h3>
              <p className="text-2xl font-bold text-blue-900">{cumulativeGPA.toFixed(2)}</p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <h3 className="text-sm font-medium text-green-600">Total Credits</h3>
              <p className="text-2xl font-bold text-green-900">
                {transcriptData.reduce((sum, course) => sum + course.weight, 0).toFixed(1)}
              </p>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <h3 className="text-sm font-medium text-purple-600">Courses Completed</h3>
              <p className="text-2xl font-bold text-purple-900">{transcriptData.length}</p>
            </div>
            <div className="bg-orange-50 p-4 rounded-lg">
              <h3 className="text-sm font-medium text-orange-600">Academic Standing</h3>
              <p className="text-2xl font-bold text-orange-900">
                {cumulativeGPA >= 3.5 ? 'Dean\'s List' : cumulativeGPA >= 2.0 ? 'Good Standing' : 'Probation'}
              </p>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="bg-white rounded-lg shadow-lg mb-6">
          <nav className="flex space-x-8 px-6">
            {['dashboard', 'analytics', 'simulator'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-4 px-2 border-b-2 font-medium text-sm capitalize ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab}
              </button>
            ))}
          </nav>
        </div>

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* GPA Trend Chart */}
            <div className="bg-white p-6 rounded-lg shadow-lg">
              <h3 className="text-lg font-semibold mb-4">Sessional GPA Trend</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={sessionalGPAs}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="term" angle={-45} textAnchor="end" height={80} />
                  <YAxis domain={[0, 4]} />
                  <Tooltip />
                  <Line 
                    type="monotone" 
                    dataKey="gpa" 
                    stroke="#2563eb" 
                    strokeWidth={3}
                    dot={{ fill: '#2563eb', strokeWidth: 2, r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Grade Distribution */}
            <div className="bg-white p-6 rounded-lg shadow-lg">
              <h3 className="text-lg font-semibold mb-4">Grade Distribution</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={gradeDistribution}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="grade" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" fill="#10b981" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Recent Courses */}
            <div className="bg-white p-6 rounded-lg shadow-lg lg:col-span-2">
              <h3 className="text-lg font-semibold mb-4">Recent Courses</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Course</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Mark</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Grade</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Credits</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">vs Course Avg</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {transcriptData.slice(-10).reverse().map((course, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {course.courseCode}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                          {course.title}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {course.mark}%
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                            ['A+', 'A', 'A-'].includes(course.grade) ? 'bg-green-100 text-green-800' :
                            ['B+', 'B', 'B-'].includes(course.grade) ? 'bg-blue-100 text-blue-800' :
                            ['C+', 'C', 'C-'].includes(course.grade) ? 'bg-yellow-100 text-yellow-800' :
                            ['D+', 'D', 'D-'].includes(course.grade) ? 'bg-orange-100 text-orange-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {course.grade}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {course.weight}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <span className={`font-medium ${
                            GRADE_POINTS[course.grade] > GRADE_POINTS[course.courseAvg] ? 'text-green-600' :
                            GRADE_POINTS[course.grade] < GRADE_POINTS[course.courseAvg] ? 'text-red-600' :
                            'text-gray-600'
                          }`}>
                            {GRADE_POINTS[course.grade] > GRADE_POINTS[course.courseAvg] ? '↑ Above' :
                             GRADE_POINTS[course.grade] < GRADE_POINTS[course.courseAvg] ? '↓ Below' :
                             '= At Average'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Performance vs Course Average */}
            <div className="bg-white p-6 rounded-lg shadow-lg">
              <h3 className="text-lg font-semibold mb-4">Performance vs Course Average</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={performanceComparison}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value}`}
                  >
                    {performanceComparison.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Sessional Analysis */}
            <div className="bg-white p-6 rounded-lg shadow-lg">
              <h3 className="text-lg font-semibold mb-4">Sessional Analysis</h3>
              <div className="space-y-4">
                {sessionalGPAs.map((session, index) => (
                  <div key={index} className="border-l-4 border-blue-500 pl-4">
                    <div className="flex justify-between items-center">
                      <h4 className="font-medium text-gray-900">{session.term}</h4>
                      <span className={`px-2 py-1 text-sm font-semibold rounded ${
                        session.gpa >= 3.5 ? 'bg-green-100 text-green-800' :
                        session.gpa >= 3.0 ? 'bg-blue-100 text-blue-800' :
                        session.gpa >= 2.0 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {session.gpa.toFixed(2)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600">
                      {session.courses} courses • {session.credits} credits
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Subject Performance */}
            <div className="bg-white p-6 rounded-lg shadow-lg lg:col-span-2">
              <h3 className="text-lg font-semibold mb-4">Subject Performance Analysis</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Strongest Subjects */}
                <div className="bg-green-50 p-4 rounded-lg">
                  <h4 className="font-medium text-green-800 mb-2">Strongest Subjects</h4>
                  <ul className="text-sm text-green-700 space-y-1">
                    <li>• MUN (Global Studies): 3.3 avg</li>
                    <li>• AMS (American Studies): 3.7 avg</li>
                    <li>• RLG (Religious Studies): 3.3</li>
                  </ul>
                </div>
                
                {/* Areas for Improvement */}
                <div className="bg-red-50 p-4 rounded-lg">
                  <h4 className="font-medium text-red-800 mb-2">Areas for Improvement</h4>
                  <ul className="text-sm text-red-700 space-y-1">
                    <li>• ECO (Economics): 0.5 avg</li>
                    <li>• CSC (Computer Science): 0.0</li>
                    <li>• STA (Statistics): 0.7</li>
                  </ul>
                </div>
                
                {/* Recommendations */}
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h4 className="font-medium text-blue-800 mb-2">Recommendations</h4>
                  <ul className="text-sm text-blue-700 space-y-1">
                    <li>• Consider retaking ECO101H1</li>
                    <li>• Seek tutoring for STEM courses</li>
                    <li>• Focus on MUN/AMS strengths</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Simulator Tab */}
        {activeTab === 'simulator' && (
          <div className="space-y-6">
            {/* GPA Simulator */}
            <div className="bg-white p-6 rounded-lg shadow-lg">
              <h3 className="text-lg font-semibold mb-4">Future GPA Simulator</h3>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium mb-3">Add Future Courses</h4>
                  {simulationCourses.map((course) => (
                    <div key={course.id} className="flex gap-2 mb-2">
                      <input
                        type="text"
                        placeholder="Course Code"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md"
                        value={course.courseCode}
                        onChange={(e) => updateSimulationCourse(course.id, 'courseCode', e.target.value)}
                      />
                      <select
                        className="px-3 py-2 border border-gray-300 rounded-md"
                        value={course.weight}
                        onChange={(e) => updateSimulationCourse(course.id, 'weight', parseFloat(e.target.value))}
                      >
                        <option value={0.5}>0.5 FCE</option>
                        <option value={1.0}>1.0 FCE</option>
                      </select>
                      <select
                        className="px-3 py-2 border border-gray-300 rounded-md"
                        value={course.expectedGrade}
                        onChange={(e) => updateSimulationCourse(course.id, 'expectedGrade', e.target.value)}
                      >
                        {Object.keys(GRADE_POINTS).map(grade => (
                          <option key={grade} value={grade}>{grade}</option>
                        ))}
                      </select>
                      <button
                        onClick={() => removeSimulationCourse(course.id)}
                        className="px-3 py-2 bg-red-500 text-white rounded-md hover:bg-red-600"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={addSimulationCourse}
                    className="w-full px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 mt-2"
                  >
                    Add Course
                  </button>
                </div>
                
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-medium mb-3">Projected Results</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span>Current GPA:</span>
                      <span className="font-bold">{cumulativeGPA.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Projected GPA:</span>
                      <span className="font-bold text-blue-600">
                        {simulateFutureGPA(simulationCourses.map(course => ({
                          ...course,
                          grade: course.expectedGrade
                        }))).toFixed(2)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>GPA Change:</span>
                      <span className={`font-bold ${
                        simulateFutureGPA(simulationCourses.map(course => ({
                          ...course,
                          grade: course.expectedGrade
                        }))) > cumulativeGPA ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {(simulateFutureGPA(simulationCourses.map(course => ({
                          ...course,
                          grade: course.expectedGrade
                        }))) - cumulativeGPA).toFixed(2)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Additional Credits:</span>
                      <span className="font-bold">
                        {simulationCourses.reduce((sum, course) => sum + course.weight, 0).toFixed(1)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Goal Calculator */}
            <div className="bg-white p-6 rounded-lg shadow-lg">
              <h3 className="text-lg font-semibold mb-4">GPA Goal Calculator</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h4 className="font-medium text-blue-800 mb-2">To Reach 3.0 GPA</h4>
                  <p className="text-sm text-blue-700">
                    Need approximately <strong>B average</strong> in next {Math.ceil((20 - transcriptData.length) / 2)} courses
                  </p>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <h4 className="font-medium text-green-800 mb-2">To Reach 3.5 GPA</h4>
                  <p className="text-sm text-green-700">
                    Need approximately <strong>A- average</strong> in next {Math.ceil((20 - transcriptData.length) / 2)} courses
                  </p>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <h4 className="font-medium text-purple-800 mb-2">Dean's List (3.5+)</h4>
                  <p className="text-sm text-purple-700">
                    {cumulativeGPA >= 3.5 ? 'Currently eligible!' : 'Need to improve performance in weak subjects'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TranscriptAnalyzer;