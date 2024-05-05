import unittest
from datetime import date, time

# Assuming your filtering functions are in a module named `scheduler`

def filter_terms_by_criteria(terms: [], part_of_day: int, clinic_id: int = None, doctor_id: int = None):
    terms_filters = get_term_filters_definitions(clinic_id, doctor_id, part_of_day)

    filtered_terms = []
    for term in terms:
        filtered_terms_for_day = list(
            filter(lambda given_term: all([term_filter(given_term) for term_filter in terms_filters]), term["visits"])
        )
        if filtered_terms_for_day:
            filtered_terms.append({"date": term["date"], "visits": filtered_terms_for_day})

    return filtered_terms


def get_term_filters_definitions(clinic_id: int, doctor_id: int, part_of_day: int):
    return [
        lambda term: term["part_of_day"] == part_of_day if part_of_day != 0 else True,
        lambda term: term["facilityId"] == clinic_id if clinic_id is not None else True,
        lambda term: term["doctorId"] == doctor_id if doctor_id is not None else True
    ]

class TestFilterTermsByCriteria(unittest.TestCase):
    def setUp(self):
        self.terms = [
            {'date': date(2024, 6, 3), 'visits': [
                {'timeFrom': time(10, 0), 'timeTo': time(10, 30), 'doctorId': 16378, 'facilityId': 2037, 'part_of_day': 1},
                {'timeFrom': time(11, 0), 'timeTo': time(11, 40), 'doctorId': 17175, 'facilityId': 2086, 'part_of_day': 1},
                {'timeFrom': time(12, 20), 'timeTo': time(13, 0), 'doctorId': 17175, 'facilityId': 2086, 'part_of_day': 2}
            ]},
            {'date': date(2024, 6, 4), 'visits': [
                {'timeFrom': time(8, 30), 'timeTo': time(9, 0), 'doctorId': 55001, 'facilityId': 2569, 'part_of_day': 1},
                {'timeFrom': time(12, 0), 'timeTo': time(12, 30), 'doctorId': 55001, 'facilityId': 2569, 'part_of_day': 2}
            ]},
            {'date': date(2024, 6, 6), 'visits': [
                {'timeFrom': time(9, 30), 'timeTo': time(10, 0), 'doctorId': 34637, 'facilityId': 2086, 'part_of_day': 1},
                {'timeFrom': time(12, 0), 'timeTo': time(12, 30), 'doctorId': 34637, 'facilityId': 2086, 'part_of_day': 2}
            ]}
        ]

    def test_filter_by_part_of_day(self):
        filtered = filter_terms_by_criteria(self.terms, part_of_day=1)
        expected_visits = sum(len(day['visits']) for day in filtered)
        self.assertEqual(expected_visits, 5)  # Check if only part_of_day 1 visits are returned

    def test_filter_by_clinic_id(self):
        filtered = filter_terms_by_criteria(self.terms, part_of_day=0, clinic_id=2086)
        expected_visits = sum(len(day['visits']) for day in filtered)
        self.assertEqual(expected_visits, 4)  # Check if only visits from clinic_id 2086 are returned

    def test_filter_by_doctor_id(self):
        filtered = filter_terms_by_criteria(self.terms, part_of_day=0, doctor_id=55001)
        expected_visits = sum(len(day['visits']) for day in filtered)
        self.assertEqual(expected_visits, 3)  # Check if only visits from doctor_id 55001 are returned

    def test_filter_by_combined_criteria(self):
        filtered = filter_terms_by_criteria(self.terms, part_of_day=2, clinic_id=2086, doctor_id=34637)
        expected_visits = sum(len(day['visits']) for day in filtered)
        self.assertEqual(expected_visits, 2)  # Check if criteria are combined correctly

    def test_filter_no_results(self):
        filtered = filter_terms_by_criteria(self.terms, part_of_day=3)
        self.assertEqual(len(filtered), 0)  # Check if no visits match part_of_day 3

if __name__ == '__main__':
    unittest.main()