"""
Unified Data Manager for PyQt6 UofT Course Dashboard
Central coordination for data synchronization across all tabs and widgets
"""

from typing import Dict, List, Optional, Any
from PyQt6.QtCore import QObject, pyqtSignal
from collections import deque
import json
import threading

class DataAction:
    """Represents a single data action for undo/redo functionality"""

    def __init__(self, action_type: str, data: Dict, description: str = ""):
        self.action_type = action_type  # 'add', 'edit', 'delete', 'bulk_edit'
        self.data = data
        self.description = description
        self.timestamp = None

class UnifiedDataManager(QObject):
    """Central data coordination with real-time synchronization"""

    # Core data signals
    course_added = pyqtSignal(dict)
    course_modified = pyqtSignal(str, dict)  # course_id, updated_data
    course_deleted = pyqtSignal(str)  # course_id

    # Progress tracking signals
    gpa_changed = pyqtSignal(float)
    credits_changed = pyqtSignal(float)
    requirement_updated = pyqtSignal(str, float)  # requirement_name, progress

    # Planning signals
    planning_updated = pyqtSignal()
    semester_changed = pyqtSignal(str, list)  # semester_id, course_list

    # System signals
    data_refreshed = pyqtSignal()
    validation_error = pyqtSignal(str, str)  # field, error_message
    operation_completed = pyqtSignal(str)  # operation_description

    def __init__(self, database):
        super().__init__()
        self.database = database
        self._lock = threading.RLock()

        # Undo/Redo system
        self.action_history = deque(maxlen=50)  # Last 50 actions
        self.redo_stack = deque(maxlen=50)

        # Cache for performance
        self._cache = {
            'transcript_courses': None,
            'gpa_data': None,
            'requirements_progress': None,
            'planning_data': None
        }
        self._cache_dirty = {
            'transcript_courses': True,
            'gpa_data': True,
            'requirements_progress': True,
            'planning_data': True
        }

    def add_course(self, course_data: Dict) -> bool:
        """Add a new course with validation and signals"""
        with self._lock:
            try:
                # Validate course data
                validation_errors = self._validate_course_data(course_data)
                if validation_errors:
                    for field, error in validation_errors.items():
                        self.validation_error.emit(field, error)
                    return False

                # Add to database
                result = self.database.save_course(course_data)
                success = result is not None

                if success:
                    # Record action for undo
                    action = DataAction('add', course_data.copy(), f"Added course {course_data.get('course_code', 'Unknown')}")
                    self.action_history.append(action)
                    self.redo_stack.clear()

                    # Invalidate cache
                    self._invalidate_cache(['transcript_courses', 'gpa_data', 'requirements_progress'])

                    # Emit signals
                    self.course_added.emit(course_data)
                    self._update_derived_data()
                    self.operation_completed.emit(f"Course {course_data.get('course_code', '')} added successfully")

                return success

            except Exception as e:
                self.validation_error.emit('general', f"Failed to add course: {str(e)}")
                return False

    def modify_course(self, course_id: str, updated_data: Dict) -> bool:
        """Modify existing course with validation and signals"""
        with self._lock:
            try:
                # Get original course data for undo
                original_course = self._get_course_by_id(course_id)
                if not original_course:
                    self.validation_error.emit('course_id', 'Course not found')
                    return False

                # Validate updated data
                validation_errors = self._validate_course_data(updated_data, is_update=True)
                if validation_errors:
                    for field, error in validation_errors.items():
                        self.validation_error.emit(field, error)
                    return False

                # Update in database
                success = self.database.update_course_in_transcript(course_id, **updated_data)

                if success:
                    # Record action for undo
                    action = DataAction('edit', {
                        'course_id': course_id,
                        'original': original_course,
                        'updated': updated_data
                    }, f"Modified course {updated_data.get('course_code', course_id)}")
                    self.action_history.append(action)
                    self.redo_stack.clear()

                    # Invalidate cache
                    self._invalidate_cache(['transcript_courses', 'gpa_data', 'requirements_progress'])

                    # Emit signals
                    self.course_modified.emit(course_id, updated_data)
                    self._update_derived_data()
                    self.operation_completed.emit(f"Course {updated_data.get('course_code', course_id)} updated")

                return success

            except Exception as e:
                self.validation_error.emit('general', f"Failed to modify course: {str(e)}")
                return False

    def delete_course(self, course_id: str) -> bool:
        """Delete course with undo capability"""
        with self._lock:
            try:
                # Get course data for undo
                course_data = self._get_course_by_id(course_id)
                if not course_data:
                    self.validation_error.emit('course_id', 'Course not found')
                    return False

                # Delete from database
                success = self.database.delete_course_from_transcript(course_id)

                if success:
                    # Record action for undo
                    action = DataAction('delete', {
                        'course_id': course_id,
                        'course_data': course_data
                    }, f"Deleted course {course_data.get('course_code', course_id)}")
                    self.action_history.append(action)
                    self.redo_stack.clear()

                    # Invalidate cache
                    self._invalidate_cache(['transcript_courses', 'gpa_data', 'requirements_progress'])

                    # Emit signals
                    self.course_deleted.emit(course_id)
                    self._update_derived_data()
                    self.operation_completed.emit(f"Course deleted")

                return success

            except Exception as e:
                self.validation_error.emit('general', f"Failed to delete course: {str(e)}")
                return False

    def get_cached_data(self, data_type: str) -> Optional[Any]:
        """Get cached data with automatic refresh if dirty"""
        if data_type not in self._cache:
            return None

        if self._cache_dirty[data_type]:
            self._refresh_cache_item(data_type)

        return self._cache[data_type]

    def refresh_all_data(self):
        """Refresh all cached data and emit signals"""
        with self._lock:
            self._invalidate_cache()
            self._refresh_all_cache()
            self._update_derived_data()
            self.data_refreshed.emit()
            self.operation_completed.emit("All data refreshed")

    def undo_last_action(self) -> bool:
        """Undo the last action"""
        with self._lock:
            if not self.action_history:
                return False

            action = self.action_history.pop()

            try:
                if action.action_type == 'add':
                    # Remove the added course
                    course_data = action.data
                    course_id = self._find_course_id(course_data)
                    if course_id:
                        self.database.delete_course_from_transcript(course_id)

                elif action.action_type == 'edit':
                    # Restore original data
                    course_id = action.data['course_id']
                    original = action.data['original']
                    self.database.update_course_in_transcript(course_id, **original)

                elif action.action_type == 'delete':
                    # Re-add the deleted course
                    course_data = action.data['course_data']
                    self.database.save_course(course_data)

                # Move to redo stack
                self.redo_stack.append(action)

                # Refresh data
                self._invalidate_cache()
                self._update_derived_data()
                self.operation_completed.emit(f"Undid: {action.description}")

                return True

            except Exception as e:
                self.validation_error.emit('undo', f"Failed to undo action: {str(e)}")
                return False

    def redo_last_action(self) -> bool:
        """Redo the last undone action"""
        with self._lock:
            if not self.redo_stack:
                return False

            action = self.redo_stack.pop()

            try:
                if action.action_type == 'add':
                    # Re-add the course
                    self.database.save_course(action.data)

                elif action.action_type == 'edit':
                    # Re-apply the edit
                    course_id = action.data['course_id']
                    updated = action.data['updated']
                    self.database.update_course_in_transcript(course_id, **updated)

                elif action.action_type == 'delete':
                    # Re-delete the course
                    course_id = action.data['course_id']
                    self.database.delete_course_from_transcript(course_id)

                # Move back to action history
                self.action_history.append(action)

                # Refresh data
                self._invalidate_cache()
                self._update_derived_data()
                self.operation_completed.emit(f"Redid: {action.description}")

                return True

            except Exception as e:
                self.validation_error.emit('redo', f"Failed to redo action: {str(e)}")
                return False

    def _validate_course_data(self, course_data: Dict, is_update: bool = False) -> Dict[str, str]:
        """Validate course data and return errors"""
        errors = {}

        # Required fields for new courses
        if not is_update:
            if not course_data.get('course_code'):
                errors['course_code'] = 'Course code is required'
            if not course_data.get('title'):
                errors['title'] = 'Course title is required'

        # Validate credits
        credits = course_data.get('credits')
        if credits is not None:
            try:
                credits_float = float(credits)
                if credits_float < 0 or credits_float > 6.0:
                    errors['credits'] = 'Credits must be between 0 and 6.0'
            except (ValueError, TypeError):
                errors['credits'] = 'Credits must be a valid number'

        # Validate grade
        grade = course_data.get('grade')
        if grade:
            valid_grades = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F', 'FZ', 'P', 'CR', 'NCR']
            if grade not in valid_grades:
                errors['grade'] = f'Grade must be one of: {", ".join(valid_grades)}'

        # Validate year
        year = course_data.get('year')
        if year is not None:
            try:
                year_int = int(year)
                if year_int < 1900 or year_int > 2100:
                    errors['year'] = 'Year must be between 1900 and 2100'
            except (ValueError, TypeError):
                errors['year'] = 'Year must be a valid integer'

        return errors

    def _get_course_by_id(self, course_id: str) -> Optional[Dict]:
        """Get course data by ID"""
        try:
            courses = self.database.get_transcript_courses()
            for course in courses:
                if str(course[0]) == str(course_id):  # Assuming first column is ID
                    return {
                        'id': course[0],
                        'course_code': course[1] if len(course) > 1 else '',
                        'title': course[2] if len(course) > 2 else '',
                        'credits': course[3] if len(course) > 3 else 0,
                        'grade': course[4] if len(course) > 4 else '',
                        'mark': course[5] if len(course) > 5 else None,
                        'session': course[6] if len(course) > 6 else '',
                        'year': course[7] if len(course) > 7 else None,
                        'status': course[8] if len(course) > 8 else ''
                    }
            return None
        except Exception:
            return None

    def _find_course_id(self, course_data: Dict) -> Optional[str]:
        """Find course ID by matching course data"""
        try:
            courses = self.database.get_transcript_courses()
            for course in courses:
                if (len(course) > 1 and course[1] == course_data.get('course_code') and
                    len(course) > 6 and course[6] == course_data.get('session') and
                    len(course) > 7 and course[7] == course_data.get('year')):
                    return str(course[0])
            return None
        except Exception:
            return None

    def _invalidate_cache(self, cache_types: List[str] = None):
        """Mark cache as dirty"""
        if cache_types is None:
            cache_types = list(self._cache_dirty.keys())

        for cache_type in cache_types:
            if cache_type in self._cache_dirty:
                self._cache_dirty[cache_type] = True

    def _refresh_cache_item(self, data_type: str):
        """Refresh specific cache item"""
        try:
            if data_type == 'transcript_courses':
                self._cache['transcript_courses'] = self.database.get_transcript_courses()
            elif data_type == 'gpa_data':
                self._cache['gpa_data'] = self._calculate_gpa_data()
            elif data_type == 'requirements_progress':
                self._cache['requirements_progress'] = self._calculate_requirements_progress()
            elif data_type == 'planning_data':
                self._cache['planning_data'] = self._get_planning_data()

            self._cache_dirty[data_type] = False

        except Exception as e:
            print(f"Error refreshing cache for {data_type}: {e}")

    def _refresh_all_cache(self):
        """Refresh all cache items"""
        for data_type in self._cache.keys():
            self._refresh_cache_item(data_type)

    def _update_derived_data(self):
        """Update derived data and emit relevant signals"""
        try:
            # Update GPA
            gpa_data = self.get_cached_data('gpa_data')
            if gpa_data:
                self.gpa_changed.emit(gpa_data.get('current_gpa', 0.0))
                self.credits_changed.emit(gpa_data.get('total_credits', 0.0))

            # Update requirements progress
            requirements = self.get_cached_data('requirements_progress')
            if requirements:
                for req_name, progress in requirements.items():
                    self.requirement_updated.emit(req_name, progress)

        except Exception as e:
            print(f"Error updating derived data: {e}")

    def _calculate_gpa_data(self) -> Dict:
        """Calculate GPA and credit statistics"""
        try:
            courses = self.database.get_transcript_courses()

            total_credits = 0
            total_points = 0
            grade_credits = 0

            grade_points = {
                'A+': 4.0, 'A': 4.0, 'A-': 3.7,
                'B+': 3.3, 'B': 3.0, 'B-': 2.7,
                'C+': 2.3, 'C': 2.0, 'C-': 1.7,
                'D+': 1.3, 'D': 1.0, 'D-': 0.7,
                'F': 0.0, 'FZ': 0.0
            }

            for course in courses:
                if len(course) > 3 and course[3]:  # Has credits
                    credits = float(course[3])
                    total_credits += credits

                    # GPA calculation
                    if len(course) > 4 and course[4] in grade_points:
                        total_points += grade_points[course[4]] * credits
                        grade_credits += credits

            current_gpa = total_points / grade_credits if grade_credits > 0 else 0.0

            return {
                'current_gpa': current_gpa,
                'total_credits': total_credits,
                'grade_credits': grade_credits,
                'total_points': total_points
            }

        except Exception as e:
            print(f"Error calculating GPA data: {e}")
            return {
                'current_gpa': 0.0,
                'total_credits': 0.0,
                'grade_credits': 0.0,
                'total_points': 0.0
            }

    def _calculate_requirements_progress(self) -> Dict[str, float]:
        """Calculate requirements progress"""
        # Placeholder implementation
        return {
            'breadth_requirements': 2.5,  # Out of 4.0 credits
            'upper_level': 8.5,  # Out of 13.0 credits
            'advanced_level': 3.0  # Out of 6.0 credits
        }

    def _get_planning_data(self) -> Dict:
        """Get course planning data"""
        # Placeholder implementation
        return {
            'semesters': [],
            'unplanned_courses': []
        }