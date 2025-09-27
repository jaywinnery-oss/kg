"""
Matching Service for Emergency Response System
Handles resource matching, location-based search, and capacity management
"""
import math
from sqlalchemy import and_, or_
from app import db
from app.models import Resource, ResourceType, EmergencyRequest, RequestStatus
from flask import current_app
from datetime import datetime, timedelta

class MatchingService:
    """Service for matching emergency requests with available resources"""
    
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """
        Calculate distance between two points using Haversine formula
        
        Args:
            lat1, lon1: Latitude and longitude of first point
            lat2, lon2: Latitude and longitude of second point
        
        Returns:
            float: Distance in kilometers
        """
        if not all([lat1, lon1, lat2, lon2]):
            return float('inf')  # Return infinite distance if coordinates missing
        
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return c * r
    
    @staticmethod
    def find_nearby_resources(resource_type, location, radius_km=50, user_lat=None, user_lon=None):
        """
        Find resources near a given location
        
        Args:
            resource_type (ResourceType): Type of resource needed
            location (str): Location string for text-based matching
            radius_km (float): Search radius in kilometers
            user_lat (float): User's latitude (optional)
            user_lon (float): User's longitude (optional)
        
        Returns:
            list: List of nearby resources sorted by distance/availability
        """
        try:
            # Base query for active resources of the specified type
            query = Resource.query.filter(
                and_(
                    Resource.resource_type == resource_type,
                    Resource.is_active == True,
                    Resource.available_capacity > 0
                )
            )
            
            # If coordinates are provided, use distance-based search
            if user_lat and user_lon:
                resources = query.all()
                
                # Calculate distances and filter by radius
                nearby_resources = []
                for resource in resources:
                    if resource.latitude and resource.longitude:
                        distance = MatchingService.calculate_distance(
                            user_lat, user_lon,
                            resource.latitude, resource.longitude
                        )
                        
                        if distance <= radius_km:
                            resource.distance = distance
                            nearby_resources.append(resource)
                
                # Sort by distance, then by available capacity
                nearby_resources.sort(key=lambda r: (r.distance, -r.available_capacity))
                
            else:
                # Use text-based location matching
                location_lower = location.lower()
                resources = query.filter(
                    or_(
                        Resource.location.ilike(f'%{location}%'),
                        Resource.location.ilike(f'%{location_lower}%')
                    )
                ).all()
                
                # Sort by available capacity (highest first)
                resources.sort(key=lambda r: -r.available_capacity)
                nearby_resources = resources
            
            current_app.logger.info(f"Found {len(nearby_resources)} resources for {resource_type.value} near {location}")
            return nearby_resources
            
        except Exception as e:
            current_app.logger.error(f"Error finding nearby resources: {e}")
            return []
    
    @staticmethod
    def match_request_to_resource(emergency_request):
        """
        Match an emergency request to the best available resource
        
        Args:
            emergency_request (EmergencyRequest): The emergency request to match
        
        Returns:
            Resource or None: Best matching resource or None if no match found
        """
        try:
            # Find nearby resources
            resources = MatchingService.find_nearby_resources(
                emergency_request.resource_type,
                emergency_request.location,
                radius_km=current_app.config.get('MAX_LOCATION_RADIUS_KM', 50),
                user_lat=emergency_request.latitude,
                user_lon=emergency_request.longitude
            )
            
            if not resources:
                return None
            
            # Apply matching algorithm
            best_resource = MatchingService._apply_matching_algorithm(
                emergency_request, resources
            )
            
            if best_resource:
                current_app.logger.info(
                    f"Matched request {emergency_request.reference_number} "
                    f"to resource {best_resource.name}"
                )
            
            return best_resource
            
        except Exception as e:
            current_app.logger.error(f"Error matching request to resource: {e}")
            return None
    
    @staticmethod
    def _apply_matching_algorithm(emergency_request, resources):
        """
        Apply matching algorithm to select best resource
        
        Args:
            emergency_request (EmergencyRequest): The emergency request
            resources (list): List of available resources
        
        Returns:
            Resource: Best matching resource
        """
        if not resources:
            return None
        
        # Scoring algorithm
        scored_resources = []
        
        for resource in resources:
            score = 0
            
            # Distance score (closer is better)
            if hasattr(resource, 'distance'):
                # Inverse distance score (max 100 points)
                distance_score = max(0, 100 - (resource.distance * 2))
                score += distance_score
            else:
                # Default score for text-based matches
                score += 50
            
            # Capacity score (more capacity is better)
            capacity_ratio = resource.available_capacity / max(resource.total_capacity, 1)
            capacity_score = capacity_ratio * 50  # Max 50 points
            score += capacity_score
            
            # Priority score based on resource type and urgency
            if emergency_request.priority_level >= 4:  # High priority
                if resource.resource_type == ResourceType.TRANSPORT:
                    score += 30  # Transport is critical for high priority
                elif resource.resource_type == ResourceType.SHELTER:
                    score += 20
            
            # Cost preference (free services get bonus points)
            if resource.price_per_unit == 0:
                score += 25  # Bonus for free services
            
            # Provider reliability score (could be based on historical data)
            # For now, just add a small random factor to break ties
            score += hash(resource.name) % 10
            
            scored_resources.append((resource, score))
        
        # Sort by score (highest first)
        scored_resources.sort(key=lambda x: x[1], reverse=True)
        
        # Return the best resource
        best_resource = scored_resources[0][0]
        
        current_app.logger.info(
            f"Best match for {emergency_request.reference_number}: "
            f"{best_resource.name} (score: {scored_resources[0][1]:.2f})"
        )
        
        return best_resource
    
    @staticmethod
    def auto_match_pending_requests():
        """
        Automatically match pending requests to available resources
        This can be run as a background task
        
        Returns:
            dict: Summary of matching results
        """
        try:
            # Get pending requests (older than 5 minutes to avoid conflicts)
            five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
            pending_requests = EmergencyRequest.query.filter(
                and_(
                    EmergencyRequest.status == RequestStatus.PENDING,
                    EmergencyRequest.created_at <= five_minutes_ago
                )
            ).order_by(EmergencyRequest.priority_level.desc(), EmergencyRequest.created_at).all()
            
            matched_count = 0
            failed_count = 0
            
            for request in pending_requests:
                try:
                    # Try to match the request
                    resource = MatchingService.match_request_to_resource(request)
                    
                    if resource:
                        # Update request status
                        request.resource_id = resource.id
                        request.status = RequestStatus.MATCHED
                        request.matched_at = datetime.utcnow()
                        request.total_cost = resource.price_per_unit
                        
                        # Update resource capacity
                        resource.update_capacity(request.quantity_needed or 1)
                        
                        matched_count += 1
                        
                        # Send notifications (in a real system, this would be queued)
                        try:
                            from app.services.sms_service import SMSService
                            
                            # Notify user
                            SMSService.send_confirmation_sms(
                                request.user.phone_number,
                                request.reference_number,
                                resource
                            )
                            
                            # Notify provider
                            if resource.contact_phone:
                                SMSService.send_provider_notification(
                                    resource.contact_phone,
                                    request,
                                    request.user
                                )
                        except Exception as e:
                            current_app.logger.error(f"Failed to send notifications: {e}")
                    
                    else:
                        failed_count += 1
                        current_app.logger.warning(
                            f"No resource found for request {request.reference_number}"
                        )
                
                except Exception as e:
                    current_app.logger.error(f"Error processing request {request.reference_number}: {e}")
                    failed_count += 1
            
            # Commit all changes
            db.session.commit()
            
            result = {
                'total_processed': len(pending_requests),
                'matched': matched_count,
                'failed': failed_count,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            current_app.logger.info(f"Auto-matching completed: {result}")
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error in auto-matching: {e}")
            db.session.rollback()
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    @staticmethod
    def get_resource_utilization_stats():
        """
        Get resource utilization statistics
        
        Returns:
            dict: Resource utilization statistics
        """
        try:
            stats = {}
            
            for resource_type in ResourceType:
                resources = Resource.query.filter(
                    and_(
                        Resource.resource_type == resource_type,
                        Resource.is_active == True
                    )
                ).all()
                
                if resources:
                    total_capacity = sum(r.total_capacity for r in resources)
                    available_capacity = sum(r.available_capacity for r in resources)
                    utilized_capacity = total_capacity - available_capacity
                    
                    utilization_rate = (utilized_capacity / total_capacity * 100) if total_capacity > 0 else 0
                    
                    stats[resource_type.value] = {
                        'total_resources': len(resources),
                        'total_capacity': total_capacity,
                        'available_capacity': available_capacity,
                        'utilized_capacity': utilized_capacity,
                        'utilization_rate': round(utilization_rate, 2)
                    }
                else:
                    stats[resource_type.value] = {
                        'total_resources': 0,
                        'total_capacity': 0,
                        'available_capacity': 0,
                        'utilized_capacity': 0,
                        'utilization_rate': 0
                    }
            
            return stats
            
        except Exception as e:
            current_app.logger.error(f"Error getting utilization stats: {e}")
            return {}
    
    @staticmethod
    def predict_resource_demand(resource_type, location, hours_ahead=24):
        """
        Predict resource demand based on historical data
        This is a simplified version - in production, you'd use ML models
        
        Args:
            resource_type (ResourceType): Type of resource
            location (str): Location to predict for
            hours_ahead (int): Hours to predict ahead
        
        Returns:
            dict: Demand prediction
        """
        try:
            # Get historical data for the same time period
            start_time = datetime.utcnow() - timedelta(days=7)  # Last 7 days
            
            historical_requests = EmergencyRequest.query.filter(
                and_(
                    EmergencyRequest.resource_type == resource_type,
                    EmergencyRequest.location.ilike(f'%{location}%'),
                    EmergencyRequest.created_at >= start_time
                )
            ).all()
            
            if not historical_requests:
                return {
                    'predicted_demand': 0,
                    'confidence': 'low',
                    'recommendation': 'Insufficient historical data'
                }
            
            # Simple prediction based on average daily demand
            daily_average = len(historical_requests) / 7
            predicted_demand = int(daily_average * (hours_ahead / 24))
            
            # Determine confidence based on data consistency
            daily_counts = {}
            for request in historical_requests:
                day = request.created_at.date()
                daily_counts[day] = daily_counts.get(day, 0) + 1
            
            if len(daily_counts) >= 5:  # At least 5 days of data
                variance = sum((count - daily_average) ** 2 for count in daily_counts.values()) / len(daily_counts)
                confidence = 'high' if variance < daily_average else 'medium'
            else:
                confidence = 'low'
            
            # Generate recommendation
            current_capacity = Resource.query.filter(
                and_(
                    Resource.resource_type == resource_type,
                    Resource.location.ilike(f'%{location}%'),
                    Resource.is_active == True
                )
            ).with_entities(db.func.sum(Resource.available_capacity)).scalar() or 0
            
            if predicted_demand > current_capacity:
                recommendation = f"Consider increasing {resource_type.value} capacity by {predicted_demand - current_capacity} units"
            else:
                recommendation = "Current capacity appears sufficient"
            
            return {
                'predicted_demand': predicted_demand,
                'current_capacity': current_capacity,
                'confidence': confidence,
                'recommendation': recommendation,
                'historical_average': round(daily_average, 2)
            }
            
        except Exception as e:
            current_app.logger.error(f"Error predicting demand: {e}")
            return {
                'error': str(e),
                'predicted_demand': 0,
                'confidence': 'error'
            }