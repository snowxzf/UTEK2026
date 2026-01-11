"""
Energy calculation module for tracking energy consumption and savings
Compares drone delivery vs traditional methods (vehicles, walking)
Includes time comparison with walking (3 mph = 4.828 km/h = 1.341 m/s)
"""
from typing import Optional, Tuple, Dict
import math
class EnergyCalculator:
    """
     energy consumption and savings for drone deliveries
    compare vs. traditional transportation methods
    """
    # Matternet M2 Drone specifications:
    # - Energy: ~1.08 Wh per meter (1.08 kWh per km) with 1 kg payload
    # - Max payload: 2 kg (approx. 4.4 lbs)
    # - Max speed: 16 m/s (57.6 km/h) - operational speeds may be lower for safety
    # - Max range: 20 km with 1 kg payload, 15 km with 2 kg payload
    # - Wind tolerance: up to 12 m/s (approx. 43 km/h) sustained winds/gusts
    # - Efficiency: UAVs are 47x more efficient in energy use than delivery vans
    # - Clean energy: UAV energy is 22x cleaner than van energy
    # ref: Matternet M2 drone specifications and research on UAV efficiency
    DRONE_ENERGY_PER_METER_BASE = 0.00108  # kWh per meter with 1 kg payload (1.08 Wh/m = 1.08 kWh/km)
    DRONE_ENERGY_BASE = 0.02  #  energy for takeoff/landing (kWh)
    # tradiitonal methods energy consumption
    # gas vehicle (hospital cart/vehicle)
    VEHICLE_ENERGY_PER_METER = 0.0003  # kWh per meter (gas equivalent)
    VEHICLE_ENERGY_BASE = 0.1  # base energy for starting vehicle
    # walking staff (if staff had to retrieve items)
    WALKING_ENERGY_PER_METER = 0.0002  # kWh per meter (human energy equivalent)
    WALKING_ENERGY_BASE = 0.001  # Minimal base energy
    #  cart (if hospital uses electric carts)
    ELECTRIC_CART_ENERGY_PER_METER = 0.00015  # kWh per meter
    ELECTRIC_CART_ENERGY_BASE = 0.05
    @staticmethod
    def calculate_drone_energy(distance_meters: float, payload_weight_kg: float = 1.0) -> float:
        """
         energy consumed by drone for a trip based on Matternet M2 specifications
         consumption increases with payload weight (non-linear relationship)
        Args:distance_meters:  distance traveled in meters, payload_weight_kg: weight of payload in kg (default 1.0 kg, max 2.0 kg)
        Returns:energy consumed in kWh
        Note:based on Matternet M2 specs: 1.08 Wh/m with 1 kg payload, energy increases with payload weight (range decreases from 20 km to 15 km when payload doubles)
        """
        #  payload to max 2 kg
        payload_weight_kg = min(max(payload_weight_kg, 0.0), 2.0)
        # ase energy for takeoff/landing
        base_energy = EnergyCalculator.DRONE_ENERGY_BASE
        # distance-based energy calculation
        # base consumption: 1.08 Wh/m = 0.00108 kWh/m with 1 kg payload
        # energy scales with payload: with 0 kg: ~0.9x, with 1 kg: 1.0x, with 2 kg: ~1.33x
        # ( from range: 20 km with 1 kg -> 15 km with 2 kg = 1.33x more energy per meter)
        if payload_weight_kg <= 0:
            # no payload  less energy
            payload_multiplier = 0.9
        elif payload_weight_kg <= 1.0:
            # linear scaling from 0.9x to 1.0x for 0-1 kg
            payload_multiplier = 0.9 + (payload_weight_kg / 1.0) * 0.1
        else:
            # non-linear scaling from 1.0x to 1.33x for 1-2 kg
            # range dec from 20 km to 15 km (ratio = 1.33)
            extra_weight = payload_weight_kg - 1.0
            payload_multiplier = 1.0 + (extra_weight / 1.0) * 0.33
        #  energy per meter with payload adjustment
        energy_per_meter = EnergyCalculator.DRONE_ENERGY_PER_METER_BASE * payload_multiplier
        # dist-based energy
        distance_energy = distance_meters * energy_per_meter
        total_energy = base_energy + distance_energy
        return total_energy
    
    @staticmethod
    def calculate_drone_energy_per_meter(payload_weight_kg: float = 1.0) -> float:
        """
        get energy consumption per meter for a given payload weight for real-time battery tracking during flight
        Args: payload_weight_kg: Weight of payload in kg (default 1.0 kg, max 2.0 kg)
        Returns: energy consumption per meter in kWh/m
        """
        # clamp payload to max 2 kg
        payload_weight_kg = min(max(payload_weight_kg, 0.0), 2.0)
        #  scaling logic as calculate_drone_energy
        if payload_weight_kg <= 0:
            payload_multiplier = 0.9
        elif payload_weight_kg <= 1.0:
            payload_multiplier = 0.9 + (payload_weight_kg / 1.0) * 0.1
        else:
            extra_weight = payload_weight_kg - 1.0
            payload_multiplier = 1.0 + (extra_weight / 1.0) * 0.33
        return EnergyCalculator.DRONE_ENERGY_PER_METER_BASE * payload_multiplier
    
    @staticmethod
    def calculate_traditional_energy(distance_meters: float, method: str = "vehicle") -> float:
        """
        Cgetalculate energy that would have been consumed by traditional method
        Args:
            distance_meters:  distance traveled in meters
            method: "vehicle", "electric_cart", or "walking"
        Returns: ergy consumed in kWh
        """
        if method == "vehicle":
            base = EnergyCalculator.VEHICLE_ENERGY_BASE
            per_meter = EnergyCalculator.VEHICLE_ENERGY_PER_METER
        elif method == "electric_cart":
            base = EnergyCalculator.ELECTRIC_CART_ENERGY_BASE
            per_meter = EnergyCalculator.ELECTRIC_CART_ENERGY_PER_METER
        elif method == "walking":
            base = EnergyCalculator.WALKING_ENERGY_BASE
            per_meter = EnergyCalculator.WALKING_ENERGY_PER_METER
        else:
            # default to vehicle
            base = EnergyCalculator.VEHICLE_ENERGY_BASE
            per_meter = EnergyCalculator.VEHICLE_ENERGY_PER_METER
        return base + (distance_meters * per_meter)
    
    @staticmethod
    def calculate_energy_savings(
        distance_meters: float,
        payload_weight_kg: float = 0.5,
        traditional_method: str = "vehicle"
    ) -> Tuple[float, float, float]:
        """
        calc energy savings from using drone vs traditional method
        Args:distance_meters: Total distance traveled in meters,payload_weight_kg: Weight of payload in kg, traditional_method: Comparison method ("vehicle", "electric_cart", "walking")
        Returns:Tuple of (drone_energy_kwh, traditional_energy_kwh, energy_saved_kwh)
        """
        drone_energy = EnergyCalculator.calculate_drone_energy(distance_meters, payload_weight_kg)
        traditional_energy = EnergyCalculator.calculate_traditional_energy(distance_meters, traditional_method)
        energy_saved = traditional_energy - drone_energy
        
        return (drone_energy, traditional_energy, energy_saved)
    
    @staticmethod
    def calculate_co2_equivalent(energy_kwh: float, energy_source: str = "grid") -> float:
        """
        calculate CO2 equivalent emissions
        UAVs use 22x cleaner energy than delivery vans
        ref: Research showing UAV energy is 22x cleaner than van energy
        Args:energy_kwh: energy in kWh, energy_source: "grid" (standard grid), "renewable" (solar/wind), "fossil"
        Returns:
            CO2 equivalent in kg
        """
        # cO2 emissions per kWh (kg CO2/kWh)
        # UAV energy is 22x cleaner than van energy (per research)
        # grid: 0.4 kg CO2/kWh for standard grid, but UAV uses cleaner sources
        # renewable: 0.0 (solar/wind), fossil: 0.8 (worst case)
        # for UAV: typically much cleaner (renewable or efficient grid)
        emissions_factor = {
            "grid": 0.4,  "renewable": 0.0,  "fossil": 0.8  # Fossil fuel heavy
        }
        factor = emissions_factor.get(energy_source, 0.4)
        return energy_kwh * factor
    
    @staticmethod
    def calculate_co2_savings_drone_vs_van(drone_energy_kwh: float, van_energy_kwh: float) -> float:
        """
        calculate CO2 savings comparing drone vs delivery van
        UAVs are 47x more efficient in energy use than delivery vans
        UAV energy is 22x cleaner than van energy
        ref: Research showing UAVs are 47x more efficient and 22x cleaner than delivery vans
        Args:
            drone_energy_kwh: Energy consumed by drone in kWh
            van_energy_kwh: Energy that would be consumed by delivery van in kWh
        Returns:
            CO2 saved in kg (positive value means drone saves CO2)
        """
        # UAV energy source (typically renewable or clean grid): 0.4 / 22 = ~0.018 kg CO2/kWh (22x cleaner)
        # Van energy source (fossil fuel): 0.8 kg CO2/kWh
        # simplified: UAV uses cleaner energy (renewable or efficient), van uses fossil
        drone_co2 = drone_energy_kwh * 0.018  # UAV energy is 22x cleaner (~0.4/22)
        van_co2 = van_energy_kwh * 0.8  # Delivery van uses fossil fuel
        co2_saved = van_co2 - drone_co2
        return max(0.0, co2_saved)  # ensure non-negative
    
    @staticmethod
    def calculate_time_comparison(
        distance_meters: float,
        drone_speed_m_per_sec: float = 2.5
    ) -> Dict[str, float]:
        """
        calc time comparison between drone delivery and walking
        walking speed: 3 mph = 4.828 km/h = 1.341 m/s
        Args:
            distance_meters: Distance traveled in meters
            drone_speed_m_per_sec: Drone speed in m/s (varies by priority: emergency 4.0, normal 2.5, low 1.5)
        Returns:Dict with walking_time_seconds, drone_time_seconds, time_saved_seconds, time_savings_percentage
        """
        WALKING_SPEED_M_PER_SEC = 3.0 * 1.60934 / 3.6  # Convert mph to m/s: 3 mph * (1.60934 km/mile) / (3.6 km/h to m/s)
        walking_time_seconds = distance_meters / WALKING_SPEED_M_PER_SEC if WALKING_SPEED_M_PER_SEC > 0 else 0.0
        drone_time_seconds = distance_meters / drone_speed_m_per_sec if drone_speed_m_per_sec > 0 else 0.0
        time_saved_seconds = walking_time_seconds - drone_time_seconds
        time_savings_percentage = (time_saved_seconds / walking_time_seconds * 100) if walking_time_seconds > 0 else 0.0
        return {
            "walking_time_seconds": round(walking_time_seconds, 2),
            "walking_time_minutes": round(walking_time_seconds / 60.0, 2),
            "drone_time_seconds": round(drone_time_seconds, 2),
            "drone_time_minutes": round(drone_time_seconds / 60.0, 2),
            "time_saved_seconds": round(time_saved_seconds, 2),
            "time_saved_minutes": round(time_saved_seconds / 60.0, 2),
            "time_savings_percentage": round(time_savings_percentage, 2),
            "speed_ratio": round(walking_time_seconds / drone_time_seconds, 2) if drone_time_seconds > 0 else 0.0  # How many times faster
        }
    
    @staticmethod
    def format_energy_report(
        drone_energy: float,traditional_energy: float,energy_saved: float,
        distance_meters: float,co2_saved: Optional[float] = None,drone_speed_m_per_sec: Optional[float] = None
    ) -> dict:
        """
         energy savings data into a report dictionary
        incl time comparison with walking (3 mph = 4.828 km/h = 1.341 m/s)
        """
        report = {
            "distance_meters": round(distance_meters, 2),"distance_km": round(distance_meters / 1000.0, 3),
            "drone_energy_kwh": round(drone_energy, 4),"traditional_energy_kwh": round(traditional_energy, 4),
            "energy_saved_kwh": round(energy_saved, 4),"energy_savings_percentage": round((energy_saved / traditional_energy * 100) if traditional_energy > 0 else 0, 2),
            "co2_saved_kg": round(co2_saved, 4) if co2_saved is not None else None
        }
        #  time comparison with walking if drone speed is provided
        if drone_speed_m_per_sec is not None and drone_speed_m_per_sec > 0:
            time_comparison = EnergyCalculator.calculate_time_comparison(
                distance_meters=distance_meters,
                drone_speed_m_per_sec=drone_speed_m_per_sec
            )
            report.update(time_comparison)
        
        return report
