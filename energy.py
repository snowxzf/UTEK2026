"""
Energy calculation module for tracking energy consumption and savings
Compares drone delivery vs traditional methods (vehicles, walking)
Includes time comparison with walking (3 mph = 4.828 km/h = 1.341 m/s)
"""
from typing import Optional, Tuple, Dict
import math


class EnergyCalculator:
    """
    Calculates energy consumption and savings for drone deliveries
    Compares against traditional transportation methods
    """
    
    # Energy constants (in kWh per unit)
    # Matternet M2 Drone Specifications:
    # - Energy consumption: ~1.08 Wh per meter (1.08 kWh per km) with 1 kg payload
    # - Max payload: 2 kg
    # - Max speed: 16 m/s (57.6 km/h)
    # - Max range: 20 km with 1 kg payload, 15 km with 2 kg payload
    # Reference: Matternet M2 drone specifications
    DRONE_ENERGY_PER_METER_BASE = 0.00108  # kWh per meter with 1 kg payload (1.08 Wh/m = 1.08 kWh/km)
    DRONE_ENERGY_BASE = 0.02  # Base energy for takeoff/landing (kWh)
    
    # Traditional methods energy consumption
    # Gas vehicle (hospital cart/vehicle)
    VEHICLE_ENERGY_PER_METER = 0.0003  # kWh per meter (gas equivalent)
    VEHICLE_ENERGY_BASE = 0.1  # Base energy for starting vehicle
    
    # Walking staff (if staff had to retrieve items)
    WALKING_ENERGY_PER_METER = 0.0002  # kWh per meter (human energy equivalent)
    WALKING_ENERGY_BASE = 0.001  # Minimal base energy
    
    # Electric cart (if hospital uses electric carts)
    ELECTRIC_CART_ENERGY_PER_METER = 0.00015  # kWh per meter
    ELECTRIC_CART_ENERGY_BASE = 0.05
    
    @staticmethod
    def calculate_drone_energy(distance_meters: float, payload_weight_kg: float = 1.0) -> float:
        """
        Calculate energy consumed by drone for a trip based on Matternet M2 specifications
        Energy consumption increases with payload weight (non-linear relationship)
        Args:
            distance_meters: Total distance traveled in meters
            payload_weight_kg: Weight of payload in kg (default 1.0 kg, max 2.0 kg)
        Returns:
            Energy consumed in kWh
        Note:
            Based on Matternet M2 specs: 1.08 Wh/m with 1 kg payload
            Energy increases with payload weight (range decreases from 20 km to 15 km when payload doubles)
        """
        # Clamp payload to max 2 kg
        payload_weight_kg = min(max(payload_weight_kg, 0.0), 2.0)
        
        # Base energy for takeoff/landing
        base_energy = EnergyCalculator.DRONE_ENERGY_BASE
        
        # Distance-based energy calculation
        # Base consumption: 1.08 Wh/m = 0.00108 kWh/m with 1 kg payload
        # Energy scales with payload: with 0 kg: ~0.9x, with 1 kg: 1.0x, with 2 kg: ~1.33x
        # (Inferred from range: 20 km with 1 kg -> 15 km with 2 kg = 1.33x more energy per meter)
        if payload_weight_kg <= 0:
            # No payload - slightly less energy
            payload_multiplier = 0.9
        elif payload_weight_kg <= 1.0:
            # Linear scaling from 0.9x to 1.0x for 0-1 kg
            payload_multiplier = 0.9 + (payload_weight_kg / 1.0) * 0.1
        else:
            # Non-linear scaling from 1.0x to 1.33x for 1-2 kg
            # Range decreases from 20 km to 15 km (ratio = 1.33)
            extra_weight = payload_weight_kg - 1.0
            payload_multiplier = 1.0 + (extra_weight / 1.0) * 0.33
        
        # Calculate energy per meter with payload adjustment
        energy_per_meter = EnergyCalculator.DRONE_ENERGY_PER_METER_BASE * payload_multiplier
        
        # Distance-based energy
        distance_energy = distance_meters * energy_per_meter
        
        total_energy = base_energy + distance_energy
        return total_energy
    
    @staticmethod
    def calculate_drone_energy_per_meter(payload_weight_kg: float = 1.0) -> float:
        """
        Calculate energy consumption per meter for a given payload weight
        Useful for real-time battery tracking during flight
        Args:
            payload_weight_kg: Weight of payload in kg (default 1.0 kg, max 2.0 kg)
        Returns:
            Energy consumption per meter in kWh/m
        """
        # Clamp payload to max 2 kg
        payload_weight_kg = min(max(payload_weight_kg, 0.0), 2.0)
        
        # Same scaling logic as calculate_drone_energy
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
        Calculate energy that would have been consumed by traditional method
        Args:
            distance_meters: Total distance traveled in meters
            method: "vehicle", "electric_cart", or "walking"
        Returns:
            Energy consumed in kWh
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
            # Default to vehicle
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
        Calculate energy savings from using drone vs traditional method
        Args:
            distance_meters: Total distance traveled in meters
            payload_weight_kg: Weight of payload in kg
            traditional_method: Comparison method ("vehicle", "electric_cart", "walking")
        Returns:
            Tuple of (drone_energy_kwh, traditional_energy_kwh, energy_saved_kwh)
        """
        drone_energy = EnergyCalculator.calculate_drone_energy(distance_meters, payload_weight_kg)
        traditional_energy = EnergyCalculator.calculate_traditional_energy(distance_meters, traditional_method)
        energy_saved = traditional_energy - drone_energy
        
        return (drone_energy, traditional_energy, energy_saved)
    
    @staticmethod
    def calculate_co2_equivalent(energy_kwh: float, energy_source: str = "grid") -> float:
        """
        Calculate CO2 equivalent emissions
        Args:
            energy_kwh: Energy in kWh
            energy_source: "grid" (standard grid), "renewable" (solar/wind), "fossil"
        Returns:
            CO2 equivalent in kg
        """
        # CO2 emissions per kWh (kg CO2/kWh)
        emissions_factor = {
            "grid": 0.4,  # Average grid mix
            "renewable": 0.0,  # Renewable energy
            "fossil": 0.8  # Fossil fuel heavy
        }
        
        factor = emissions_factor.get(energy_source, 0.4)
        return energy_kwh * factor
    
    @staticmethod
    def calculate_time_comparison(
        distance_meters: float,
        drone_speed_m_per_sec: float = 2.5
    ) -> Dict[str, float]:
        """
        Calculate time comparison between drone delivery and walking
        Walking speed: 3 mph = 4.828 km/h = 1.341 m/s
        Args:
            distance_meters: Distance traveled in meters
            drone_speed_m_per_sec: Drone speed in m/s (varies by priority: emergency 4.0, normal 2.5, low 1.5)
        Returns:
            Dict with walking_time_seconds, drone_time_seconds, time_saved_seconds, time_savings_percentage
        """
        # Walking speed: 3 mph = 3 * 1.60934 km/h = 4.828 km/h = 1.341 m/s
        WALKING_SPEED_M_PER_SEC = 3.0 * 1.60934 / 3.6  # Convert mph to m/s: 3 mph * (1.60934 km/mile) / (3.6 km/h to m/s)
        
        # Calculate times
        walking_time_seconds = distance_meters / WALKING_SPEED_M_PER_SEC if WALKING_SPEED_M_PER_SEC > 0 else 0.0
        drone_time_seconds = distance_meters / drone_speed_m_per_sec if drone_speed_m_per_sec > 0 else 0.0
        
        # Time saved (walking time - drone time)
        time_saved_seconds = walking_time_seconds - drone_time_seconds
        
        # Time savings percentage
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
        drone_energy: float,
        traditional_energy: float,
        energy_saved: float,
        distance_meters: float,
        co2_saved: Optional[float] = None,
        drone_speed_m_per_sec: Optional[float] = None
    ) -> dict:
        """
        Format energy savings data into a report dictionary
        Includes time comparison with walking (3 mph = 4.828 km/h = 1.341 m/s)
        """
        report = {
            "distance_meters": round(distance_meters, 2),
            "distance_km": round(distance_meters / 1000.0, 3),
            "drone_energy_kwh": round(drone_energy, 4),
            "traditional_energy_kwh": round(traditional_energy, 4),
            "energy_saved_kwh": round(energy_saved, 4),
            "energy_savings_percentage": round((energy_saved / traditional_energy * 100) if traditional_energy > 0 else 0, 2),
            "co2_saved_kg": round(co2_saved, 4) if co2_saved is not None else None
        }
        
        # Add time comparison with walking if drone speed is provided
        if drone_speed_m_per_sec is not None and drone_speed_m_per_sec > 0:
            time_comparison = EnergyCalculator.calculate_time_comparison(
                distance_meters=distance_meters,
                drone_speed_m_per_sec=drone_speed_m_per_sec
            )
            report.update(time_comparison)
        
        return report
