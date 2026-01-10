"""
 data model and dataset for hospital drone logistics system
based on patient prioritization tools (PPT) research
ref: Dery et al. (2020) - A systematic review of patient prioritization tools in non-emergency healthcare services
"""
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Tuple
from enum import Enum
import random
class HealthRiskLevel(Enum):
    """health risk assessment levels"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"
class CurrentStatus(Enum):
    """curr patient status"""
    STABLE = "stable"
    MONITORING = "monitoring"
    CRITICAL = "critical"
    IMPROVING = "improving"
    DETERIORATING = "deteriorating"
@dataclass
class Vitals:
    """ vital signs with timestamp"""
    timestamp: datetime = field(default_factory=datetime.now)
    heart_rate: Optional[int] = None  # bpm
    blood_pressure_systolic: Optional[int] = None  # mmHg
    blood_pressure_diastolic: Optional[int] = None  # mmHg
    temperature: Optional[float] = None  # Celsius
    oxygen_saturation: Optional[float] = None  # percentage
    respiratory_rate: Optional[int] = None  # breaths per minute
    pain_level: Optional[int] = None  # 0-10 scale

@dataclass
class Patient:
    """
     patient data model for prioritizationBased on PPT research characteristics
    ref: Dery et al. (2020)
    """
    #  Main Details
    patient_id: str
    symptoms: str
    current_vitals: Optional[Vitals] = None
    vitals_history: List[Vitals] = field(default_factory=list)  # History of vitals over time
    current_status: CurrentStatus = CurrentStatus.STABLE
    reason_for_hospitalization: str = ""
    # demo Data
    name: str = ""
    date_of_birth: Optional[date] = None
    gender: str = ""  # Male, Female, Other
    address: str = ""
    emergency_contact: str = ""
    # admin Data
    date_of_admission: Optional[date] = None
    expected_discharge_date: Optional[date] = None
    family_doctor: str = ""
    insurance_details: str = ""
    # health Risks
    health_risks: List[str] = field(default_factory=list)  # e.g., ["diabetes", "hypertension"]
    lifestyle_risks: List[str] = field(default_factory=list)  # e.g., ["smoking", "sedentary"]
    allergies: List[str] = field(default_factory=list)
    #  med History
    medical_history: List[str] = field(default_factory=list)
    past_diagnostics: List[str] = field(default_factory=list)
    past_medications: List[str] = field(default_factory=list)
    immunization_history: List[str] = field(default_factory=list)
    #  Plans
    treatment_plans: List[str] = field(default_factory=list)
    @property
    def age(self) -> Optional[int]:
        """get age from date of birth"""
        if self.date_of_birth:
            today = date.today()
            age = today.year - self.date_of_birth.year
            if today.month < self.date_of_birth.month or (today.month == self.date_of_birth.month and today.day < self.date_of_birth.day):
                age -= 1
            return age
        return None
    @property
    def days_in_hospital(self) -> Optional[int]:
        """get days since admission"""
        if self.date_of_admission:
            today = date.today()
            delta = today - self.date_of_admission
            return delta.days
        return None
    @property
    def is_critical_vitals(self) -> bool:
        """check if vitals indicate critical condition"""
        if not self.current_vitals:
            return False
        v = self.current_vitals
        # crit thresholds based on medical standards
        if v.heart_rate and (v.heart_rate < 50 or v.heart_rate > 120):
            return True
        if v.blood_pressure_systolic and (v.blood_pressure_systolic < 90 or v.blood_pressure_systolic > 180):
            return True
        if v.temperature and (v.temperature < 35.0 or v.temperature > 39.0):
            return True
        if v.oxygen_saturation and v.oxygen_saturation < 90:
            return True
        if v.pain_level and v.pain_level >= 7:
            return True
        return False
    
    @property
    def risk_score(self) -> float:
        """get overall health risk score (0-1)"""
        score = 0.0
        # curr status
        status_scores = {
            CurrentStatus.CRITICAL: 1.0,
            CurrentStatus.DETERIORATING: 0.75,
            CurrentStatus.MONITORING: 0.5,
            CurrentStatus.IMPROVING: 0.25,
            CurrentStatus.STABLE: 0.1
        }
        score += status_scores.get(self.current_status, 0.0) * 0.3
        # crit vitals
        if self.is_critical_vitals:
            score += 0.
        # health risks
        score += min(len(self.health_risks) * 0.1, 0.2)
        # lifestyle risks
        score += min(len(self.lifestyle_risks) * 0.05, 0.1)
        # age factor (very young or very old = higher risk)
        if self.age:
            if self.age < 2 or self.age > 75:
                score += 0.1
        return min(score, 1.0)
    @property
    def needs_urgency(self) -> bool:
        """ if patient needs urgent care based on PPT criteria"""
        return (
            self.current_status == CurrentStatus.CRITICAL or
            self.is_critical_vitals or
            self.risk_score >= 0.7
        )
    def update_vitals_over_time(self, hours_since_admission: float) -> None:
        """
         vitals changes over time based on patient condition
        """
        if not self.current_vitals:
            return
        base = self.current_vitals
        trend = self._get_vitals_trend(hours_since_admission)
        new_vitals = Vitals(timestamp=datetime.now())
        if base.heart_rate is not None:
            new_vitals.heart_rate = self._apply_trend(
                base.heart_rate, trend['hr'], min_val=50, max_val=150,variability=5
            )
        if base.blood_pressure_systolic is not None:
            new_vitals.blood_pressure_systolic = self._apply_trend(
                base.blood_pressure_systolic, trend['bp_sys'],min_val=80, max_val=200,variability=8
            )
        if base.blood_pressure_diastolic is not None:
            new_vitals.blood_pressure_diastolic = self._apply_trend(
                base.blood_pressure_diastolic, trend['bp_dia'],min_val=50, max_val=120,variability=5
            )
        if base.temperature is not None:
            new_vitals.temperature = self._apply_trend(base.temperature, trend['temp'],
                min_val=35.0, max_val=40.5,variability=0.3
            )
        if base.oxygen_saturation is not None:
            new_vitals.oxygen_saturation = self._apply_trend(
                base.oxygen_saturation, trend['o2'],min_val=85.0, max_val=100.0,variability=2.0
            )
        if base.respiratory_rate is not None:
            new_vitals.respiratory_rate = self._apply_trend(
                base.respiratory_rate, trend['rr'],min_val=10, max_val=35,variability=2
            )
        if base.pain_level is not None:
            new_vitals.pain_level = self._apply_trend(
                base.pain_level, trend['pain'],min_val=0, max_val=10,variability=1
            )
        # pduate current vitals and add to history
        self.current_vitals = new_vitals
        self.vitals_history.append(new_vitals)
        #  only last 100 readings to prevent memory issues
        if len(self.vitals_history) > 100:
            self.vitals_history = self.vitals_history[-100:]
        #  status based on vitals
        self._update_status_from_vitals()
    
    def _get_vitals_trend(self, hours_since_admission: float) -> Dict[str, float]:
        """Determine how vitals should change based on patient status and time"""
        trends = {
            'hr': 0.0,      # heart rate trend (-1 to 1)
            'bp_sys': 0.0,  # syst BP trend
            'bp_dia': 0.0,  # diastol BP trend
            'temp': 0.0,    # temp trend
            'o2': 0.0,      # o2 saturation trend
            'rr': 0.0,      # resp rate trend
            'pain': 0.0     # pain level trend
        }
        
        # Status-based trends
        if self.current_status == CurrentStatus.IMPROVING:
            trends['hr'] = -0.3  # dec (getting better)
            trends['bp_sys'] = -0.2
            trends['temp'] = -0.4
            trends['o2'] = 0.3   # inc (getting better)
            trends['rr'] = -0.3
            trends['pain'] = -0.4
        elif self.current_status == CurrentStatus.DETERIORATING:
            trends['hr'] = 0.4   # inc (getting worse)
            trends['bp_sys'] = 0.3
            trends['temp'] = 0.4
            trends['o2'] = -0.4  # dec (getting worse)
            trends['rr'] = 0.4
            trends['pain'] = 0.4
        elif self.current_status == CurrentStatus.CRITICAL:
            # crit patients fluctuate more
            trends['hr'] = random.uniform(-0.2, 0.3)
            trends['bp_sys'] = random.uniform(-0.2, 0.3)
            trends['temp'] = random.uniform(-0.2, 0.3)
            trends['o2'] = random.uniform(-0.3, 0.2)
            trends['rr'] = random.uniform(-0.2, 0.3)
            trends['pain'] = random.uniform(-0.2, 0.3)
        elif self.current_status == CurrentStatus.STABLE:
            # stable patients trend towards normal slowly
            trends['hr'] = -0.1
            trends['bp_sys'] = -0.1
            trends['temp'] = -0.2
            trends['o2'] = 0.1
            trends['rr'] = -0.1
            trends['pain'] = -0.2
        
        # time-based recovery (longer in hospital = more recovery)
        recovery_factor = min(hours_since_admission / 72.0, 1.0)  # Max recovery after 3 days
        for key in trends:
            if key in ['o2']:  # o2 improves over time
                trends[key] += 0.1 * recovery_factor
            elif key in ['hr', 'bp_sys', 'temp', 'rr', 'pain']:  # others decrease
                trends[key] -= 0.1 * recovery_factor
        return trends
    
    def _apply_trend(self, current_value: float, trend: float, 
                     min_val: float, max_val: float, variability: float) -> float:
        """ trend to a vital sign value with natural variability"""
        #  change
        change = (max_val - min_val) * trend * 0.1
        #  natural variability (random walk)
        variability_change = random.uniform(-variability, variability)
        new_value = current_value + change + variability_change
        # clamp to valid range
        if isinstance(current_value, float):
            return max(min_val, min(max_val, round(new_value, 1)))
        else:
            return int(max(min_val, min(max_val, round(new_value))))
    
    def _update_status_from_vitals(self) -> None:
        """ patient status based on current vitals"""
        if not self.current_vitals:
            return
        v = self.current_vitals
        critical_count = 0
        # cehck for critical vitals
        if v.heart_rate and (v.heart_rate < 50 or v.heart_rate > 120):
            critical_count += 1
        if v.blood_pressure_systolic and (v.blood_pressure_systolic < 90 or v.blood_pressure_systolic > 180):
            critical_count += 1
        if v.temperature and (v.temperature < 35.0 or v.temperature > 39.0):
            critical_count += 1
        if v.oxygen_saturation and v.oxygen_saturation < 92:
            critical_count += 1
        if v.pain_level and v.pain_level >= 8:
            critical_count += 1
        # update status based on critical vitals
        if critical_count >= 3:
            self.current_status = CurrentStatus.CRITICAL
        elif critical_count >= 2:
            self.current_status = CurrentStatus.DETERIORATING
        elif critical_count == 0:
            # check if improving
            if v.oxygen_saturation and v.oxygen_saturation > 97 and v.temperature and 36.5 <= v.temperature <= 37.5:
                if self.current_status == CurrentStatus.DETERIORATING or self.current_status == CurrentStatus.CRITICAL:
                    self.current_status = CurrentStatus.IMPROVING
    def generate_vitals_history(self, hours_ago: int = 24, interval_minutes: int = 30) -> None:
        """gen vitals history for the past N hours with specified interval"""
        if not self.current_vitals or not self.date_of_admission:
            return
        now = datetime.now()
        admission_time = datetime.combine(self.date_of_admission, datetime.min.time())
        # gen vitals at each interval
        for i in range((hours_ago * 60) // interval_minutes):
            hours_since_admission = (now - timedelta(minutes=i * interval_minutes) - admission_time).total_seconds() / 3600.0
            if hours_since_admission < 0:
                continue
            # make vitals entry for this time point
            time_point = now - timedelta(minutes=i * interval_minutes)
            vitals_at_time = Vitals(timestamp=time_point)
            # cpy current vitals as base (we'll simulate from there backwards)
            base_vitals = self.current_vitals
            vitals_at_time.heart_rate = base_vitals.heart_rate
            vitals_at_time.blood_pressure_systolic = base_vitals.blood_pressure_systolic
            vitals_at_time.blood_pressure_diastolic = base_vitals.blood_pressure_diastolic
            vitals_at_time.temperature = base_vitals.temperature
            vitals_at_time.oxygen_saturation = base_vitals.oxygen_saturation
            vitals_at_time.respiratory_rate = base_vitals.respiratory_rate
            vitals_at_time.pain_level = base_vitals.pain_level
            # sim backwards in time (opposite trend)
            trend = self._get_vitals_trend(hours_since_admission)
            # rev trend for historical data
            reverse_trend = {k: -v * 0.5 for k, v in trend.items()}
            if vitals_at_time.heart_rate:
                vitals_at_time.heart_rate = self._apply_trend(
                    vitals_at_time.heart_rate, reverse_trend['hr'],
                    min_val=50, max_val=150, variability=5
                )
            if vitals_at_time.blood_pressure_systolic:
                vitals_at_time.blood_pressure_systolic = self._apply_trend(
                    vitals_at_time.blood_pressure_systolic, reverse_trend['bp_sys'],
                    min_val=80, max_val=200, variability=8
                )
            if vitals_at_time.blood_pressure_diastolic:
                vitals_at_time.blood_pressure_diastolic = self._apply_trend(
                    vitals_at_time.blood_pressure_diastolic, reverse_trend['bp_dia'],
                    min_val=50, max_val=120, variability=5
                )
            if vitals_at_time.temperature:
                vitals_at_time.temperature = self._apply_trend(
                    vitals_at_time.temperature, reverse_trend['temp'],
                    min_val=35.0, max_val=40.5, variability=0.3
                )
            if vitals_at_time.oxygen_saturation:
                vitals_at_time.oxygen_saturation = self._apply_trend(
                    vitals_at_time.oxygen_saturation, reverse_trend['o2'],
                    min_val=85.0, max_val=100.0, variability=2.0
                )
            if vitals_at_time.respiratory_rate:
                vitals_at_time.respiratory_rate = self._apply_trend(
                    vitals_at_time.respiratory_rate, reverse_trend['rr'],
                    min_val=10, max_val=35, variability=2
                )
            if vitals_at_time.pain_level:
                vitals_at_time.pain_level = self._apply_trend(
                    vitals_at_time.pain_level, reverse_trend['pain'],
                    min_val=0, max_val=10, variability=1
                )
            self.vitals_history.append(vitals_at_time)
        # sort by timestamp (oldest first)
        self.vitals_history.sort(key=lambda v: v.timestamp)

#generated patient database
class PatientDatabase:
    """
    patient database with sample data for testing
    """
    @staticmethod
    def create_sample_patients() -> Dict[str, Patient]:
        """make a sample dataset of patients"""
        from datetime import timedelta
        today = date.today()
        patients = {}
        # patient 1: Elderly critical cardiac patient
        patients["P001"] = Patient(
            patient_id="P001",
            name="John Smith",
            date_of_birth=date(1945, 3, 15),
            gender="Male",
            address="123 Main St, City",
            emergency_contact="Mary Smith (Wife) - 555-0101",
            date_of_admission=today - timedelta(days=2),
            expected_discharge_date=today + timedelta(days=5),
            family_doctor="Dr. Johnson",
            insurance_details="Medicare - Policy #12345",
            symptoms="Chest pain, shortness of breath, dizziness",
            current_vitals=Vitals(
                heart_rate=105,
                blood_pressure_systolic=150,
                blood_pressure_diastolic=95,
                temperature=37.8,
                oxygen_saturation=92,
                respiratory_rate=22,
                pain_level=6
            ),
            current_status=CurrentStatus.CRITICAL,
            reason_for_hospitalization="Acute myocardial infarction, cardiac monitoring",
            health_risks=["hypertension", "coronary_artery_disease", "diabetes"],
            lifestyle_risks=["smoking_history"],
            allergies=["penicillin"],
            medical_history=["Heart attack (2018)", "Diabetes Type 2", "Hypertension"],
            past_medications=["Metformin", "Aspirin", "Atorvastatin"],
            treatment_plans=["Cardiac monitoring", "Medication adjustment", "Dietary consultation"]
        )
        #  2: Young adult with appendicitis
        patients["P002"] = Patient(
            patient_id="P002",
            name="Sarah Johnson",
            date_of_birth=date(1998, 7, 22),
            gender="Female",
            address="456 Oak Ave, City",
            emergency_contact="Robert Johnson (Father) - 555-0202",
            date_of_admission=today - timedelta(days=1),
            expected_discharge_date=today + timedelta(days=2),
            family_doctor="Dr. Williams",
            insurance_details="Blue Cross - Policy #67890",
            symptoms="Severe abdominal pain, nausea, fever",
            current_vitals=Vitals(
                heart_rate=95,
                blood_pressure_systolic=120,
                blood_pressure_diastolic=80,
                temperature=38.5,
                oxygen_saturation=98,
                respiratory_rate=18,
                pain_level=8
            ),
            current_status=CurrentStatus.MONITORING,
            reason_for_hospitalization="Acute appendicitis, post-operative recovery",
            health_risks=["obesity"],
            lifestyle_risks=["sedentary"],
            allergies=["latex"],
            medical_history=["Appendectomy (2024)"],
            past_medications=["Ibuprofen"],
            treatment_plans=["Post-op monitoring", "Pain management", "Wound care"]
        )
        
        # Patient 3: Middle-aged parent with pneumonia
        patients["P003"] = Patient(
            patient_id="P003",
            name="Michael Chen",
            date_of_birth=date(1980, 11, 8),
            gender="Male",
            address="789 Elm St, City",
            emergency_contact="Lisa Chen (Wife) - 555-0303",
            date_of_admission=today - timedelta(days=3),
            expected_discharge_date=today + timedelta(days=3),
            family_doctor="Dr. Brown",
            insurance_details="Aetna - Policy #11111",
            symptoms="Cough, fever, difficulty breathing, fatigue",
            current_vitals=Vitals(
                heart_rate=88,
                blood_pressure_systolic=130,
                blood_pressure_diastolic=85,
                temperature=38.2,
                oxygen_saturation=94,
                respiratory_rate=20,
                pain_level=4
            ),
            current_status=CurrentStatus.MONITORING,
            reason_for_hospitalization="Pneumonia, respiratory support needed",
            health_risks=["asthma"],
            lifestyle_risks=[],
            allergies=["shellfish"],
            medical_history=["Asthma", "Previous pneumonia (2020)"],
            past_medications=["Albuterol inhaler", "Prednisone"],
            immunization_history=["COVID-19 (2021)", "Influenza (2023)"],
            treatment_plans=["Antibiotics", "Oxygen therapy", "Chest physiotherapy"]
        )
        
        # Patient 4: Elderly stroke patient
        patients["P004"] = Patient(
            patient_id="P004",
            name="Margaret Wilson",
            date_of_birth=date(1940, 5, 12),
            gender="Female",
            address="321 Pine Rd, City",
            emergency_contact="Thomas Wilson (Son) - 555-0404",
            date_of_admission=today - timedelta(days=5),
            expected_discharge_date=today + timedelta(days=10),
            family_doctor="Dr. Davis",
            insurance_details="Medicare - Policy #22222",
            symptoms="Weakness on left side, speech difficulties, confusion",
            current_vitals=Vitals(
                heart_rate=75,
                blood_pressure_systolic=165,
                blood_pressure_diastolic=100,
                temperature=36.8,
                oxygen_saturation=96,
                respiratory_rate=16,
                pain_level=2
            ),
            current_status=CurrentStatus.IMPROVING,
            reason_for_hospitalization="Cerebrovascular accident (stroke), rehabilitation",
            health_risks=["hypertension", "atrial_fibrillation", "diabetes"],
            lifestyle_risks=[],
            allergies=["aspirin"],
            medical_history=["Stroke (2024)", "Hypertension", "Diabetes Type 2", "Atrial Fibrillation"],
            past_medications=["Warfarin", "Metformin", "Lisinopril"],
            past_diagnostics=["MRI brain", "Echocardiogram", "Carotid ultrasound"],
            treatment_plans=["Physical therapy", "Speech therapy", "Anticoagulation", "Blood pressure management"]
        )
        
        # Patient 5: Young child with asthma
        patients["P005"] = Patient(
            patient_id="P005",
            name="Emma Martinez",
            date_of_birth=date(2020, 9, 3),
            gender="Female",
            address="654 Maple Ln, City",
            emergency_contact="Carlos Martinez (Father) - 555-0505",
            date_of_admission=today - timedelta(days=1),
            expected_discharge_date=today + timedelta(days=1),
            family_doctor="Dr. Anderson (Pediatrician)",
            insurance_details="Medicaid - Policy #33333",
            symptoms="Wheezing, cough, difficulty breathing, rapid breathing",
            current_vitals=Vitals(
                heart_rate=120,
                blood_pressure_systolic=100,
                blood_pressure_diastolic=65,
                temperature=37.5,
                oxygen_saturation=91,
                respiratory_rate=32,
                pain_level=5
            ),
            current_status=CurrentStatus.CRITICAL,
            reason_for_hospitalization="Severe asthma exacerbation, respiratory distress",
            health_risks=["asthma", "eczema"],
            lifestyle_risks=[],
            allergies=["peanuts", "dust_mites"],
            medical_history=["Asthma (since age 2)", "Eczema", "Food allergies"],
            past_medications=["Albuterol nebulizer", "Fluticasone inhaler"],
            immunization_history=["All routine childhood immunizations"],
            treatment_plans=["Nebulizer treatments", "Corticosteroids", "Oxygen support", "Parent education"]
        )
        
        # Patient 6: Adult with fracture
        patients["P006"] = Patient(
            patient_id="P006",
            name="David Lee",
            date_of_birth=date(1992, 2, 18),
            gender="Male",
            address="987 Cedar Blvd, City",
            emergency_contact="Jennifer Lee (Sister) - 555-0606",
            date_of_admission=today - timedelta(days=0),
            expected_discharge_date=today + timedelta(days=1),
            family_doctor="Dr. Taylor",
            insurance_details="United Healthcare - Policy #44444",
            symptoms="Right leg pain, inability to bear weight, swelling",
            current_vitals=Vitals(
                heart_rate=72,
                blood_pressure_systolic=118,
                blood_pressure_diastolic=75,
                temperature=36.9,
                oxygen_saturation=99,
                respiratory_rate=16,
                pain_level=7
            ),
            current_status=CurrentStatus.STABLE,
            reason_for_hospitalization="Right tibia fracture from fall, surgical fixation planned",
            health_risks=[],
            lifestyle_risks=["active_sports"],
            allergies=[],
            medical_history=["Previous ankle sprain (2022)"],
            past_diagnostics=["X-ray right leg"],
            treatment_plans=["Surgical fixation", "Pain management", "Pre-op preparation"]
        )
        
        # Patient 7: Elderly with infection
        patients["P007"] = Patient(
            patient_id="P007",
            name="Robert Taylor",
            date_of_birth=date(1938, 12, 25),
            gender="Male",
            address="147 Birch Dr, City",
            emergency_contact="Susan Taylor (Daughter) - 555-0707",
            date_of_admission=today - timedelta(days=2),
            expected_discharge_date=today + timedelta(days=5),
            family_doctor="Dr. Miller",
            insurance_details="Medicare - Policy #55555",
            symptoms="Confusion, fever, urinary symptoms, weakness",
            current_vitals=Vitals(
                heart_rate=92,
                blood_pressure_systolic=140,
                blood_pressure_diastolic=88,
                temperature=38.8,
                oxygen_saturation=95,
                respiratory_rate=20,
                pain_level=3
            ),
            current_status=CurrentStatus.MONITORING,
            reason_for_hospitalization="Urinary tract infection with sepsis, dehydration",
            health_risks=["diabetes", "kidney_disease", "hypertension"],
            lifestyle_risks=[],
            allergies=["sulfa_drugs"],
            medical_history=["Type 2 Diabetes", "Chronic kidney disease", "Hypertension", "Prostate enlargement"],
            past_medications=["Insulin", "Furosemide", "Metformin"],
            past_diagnostics=["Urine culture", "Blood cultures", "Kidney function tests"],
            treatment_plans=["Antibiotics IV", "Fluid replacement", "Diabetes management", "Sepsis monitoring"]
        )
        
        # Patient 8: Post-surgical patient
        patients["P008"] = Patient(
            patient_id="P008",
            name="Jennifer Adams",
            date_of_birth=date(1975, 6, 30),
            gender="Female",
            address="258 Spruce Way, City",
            emergency_contact="Mark Adams (Husband) - 555-0808",
            date_of_admission=today - timedelta(days=1),
            expected_discharge_date=today + timedelta(days=2),
            family_doctor="Dr. White",
            insurance_details="Cigna - Policy #66666",
            symptoms="Post-operative pain, nausea, fatigue",
            current_vitals=Vitals(
                heart_rate=78,
                blood_pressure_systolic=115,
                blood_pressure_diastolic=70,
                temperature=37.2,
                oxygen_saturation=98,
                respiratory_rate=14,
                pain_level=5
            ),
            current_status=CurrentStatus.IMPROVING,
            reason_for_hospitalization="Laparoscopic cholecystectomy, post-op recovery",
            health_risks=["obesity"],
            lifestyle_risks=["sedentary"],
            allergies=["morphine"],
            medical_history=["Gallbladder disease", "Previous abdominal surgery"],
            past_medications=["Acetaminophen", "Ondansetron"],
            treatment_plans=["Pain management", "Wound care", "Mobility exercises", "Diet progression"]
        )
        
        # Generate vitals history for all patients
        for patient in patients.values():
            if patient.date_of_admission and patient.current_vitals:
                # Generate 24 hours of history at 30-minute intervals
                patient.generate_vitals_history(hours_ago=24, interval_minutes=30)
                # Update current vitals to latest (most recent)
                if patient.vitals_history:
                    patient.current_vitals = patient.vitals_history[-1]
        
        return patients
#  patient database instance
_patient_database: Optional[Dict[str, Patient]] = None
def get_patient_database() -> Dict[str, Patient]:
    """Get or create the patient database"""
    global _patient_database
    if _patient_database is None:
        _patient_database = PatientDatabase.create_sample_patients()
def get_patient(patient_id: str) -> Optional[Patient]:
    """Get a patient by ID"""
    return get_patient_database().get(patient_id)
def get_all_patients() -> List[Patient]:
    """Get all patients"""
    return list(get_patient_database().values())
