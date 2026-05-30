"""
Skills matching system for Worker Connect.

Advanced matching algorithm for pairing jobs with workers based on skills.
"""

from django.db.models import Q
from typing import List, Dict, Any, Set, Tuple
import re


class SkillsMatcher:
    """
    Advanced skills matching for job-worker pairing.
    """
    
    # Skill categories and related skills
    SKILL_CATEGORIES = {
        'construction': {
            'carpentry', 'plumbing', 'electrical', 'roofing', 'painting',
            'drywall', 'masonry', 'flooring', 'hvac', 'welding', 'framing',
            'concrete', 'demolition', 'remodeling', 'renovation'
        },
        'cleaning': {
            'house cleaning', 'office cleaning', 'carpet cleaning',
            'window cleaning', 'deep cleaning', 'sanitization',
            'janitorial', 'pressure washing', 'move out cleaning'
        },
        'landscaping': {
            'lawn care', 'gardening', 'tree trimming', 'landscaping',
            'irrigation', 'lawn mowing', 'hedge trimming', 'leaf removal',
            'snow removal', 'yard work'
        },
        'moving': {
            'moving', 'packing', 'loading', 'unloading', 'furniture assembly',
            'heavy lifting', 'junk removal', 'hauling', 'delivery'
        },
        'handyman': {
            'general repairs', 'assembly', 'mounting', 'installation',
            'minor repairs', 'maintenance', 'home repair', 'fix-it'
        },
        'technical': {
            'computer repair', 'it support', 'networking', 'smart home',
            'electronics', 'appliance repair', 'tv mounting'
        },
        'automotive': {
            'car repair', 'oil change', 'tire change', 'auto detailing',
            'car wash', 'mechanic', 'body work'
        },
        'events': {
            'event setup', 'catering', 'bartending', 'serving', 'dj',
            'photography', 'videography', 'event planning'
        },
    }
    
    # Skill synonyms for matching
    SKILL_SYNONYMS = {
        'carpenter': 'carpentry',
        'plumber': 'plumbing',
        'electrician': 'electrical',
        'painter': 'painting',
        'roofer': 'roofing',
        'hvac technician': 'hvac',
        'welder': 'welding',
        'mason': 'masonry',
        'cleaner': 'cleaning',
        'mover': 'moving',
        'gardener': 'gardening',
        'landscaper': 'landscaping',
        'handyperson': 'handyman',
        'it': 'it support',
        'tech support': 'it support',
    }
    
    @classmethod
    def extract_skills(cls, text: str) -> Set[str]:
        """
        Extract skills from text (job description, worker profile, etc).
        
        Returns normalized set of skills.
        """
        if not text:
            return set()
        
        text = text.lower()
        found_skills = set()
        
        # Check all known skills
        all_skills = set()
        for category_skills in cls.SKILL_CATEGORIES.values():
            all_skills.update(category_skills)
        
        for skill in all_skills:
            if skill in text:
                found_skills.add(skill)
        
        # Check synonyms
        for synonym, canonical in cls.SKILL_SYNONYMS.items():
            if synonym in text:
                found_skills.add(canonical)
        
        return found_skills
    
    @classmethod
    def normalize_skill(cls, skill: str) -> str:
        """Normalize a skill to its canonical form."""
        skill = skill.lower().strip()
        return cls.SKILL_SYNONYMS.get(skill, skill)
    
    @classmethod
    def get_skill_category(cls, skill: str) -> str | None:
        """Get the category for a skill."""
        skill = cls.normalize_skill(skill)
        
        for category, skills in cls.SKILL_CATEGORIES.items():
            if skill in skills:
                return category
        
        return None
    
    @classmethod
    def get_related_skills(cls, skill: str) -> Set[str]:
        """Get skills related to the given skill."""
        category = cls.get_skill_category(skill)
        
        if category:
            return cls.SKILL_CATEGORIES[category]
        
        return {skill}
    
    @classmethod
    def calculate_skill_match(
        cls,
        worker_skills: List[str],
        job_skills: List[str],
        require_exact: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate skill match between worker and job.
        
        Args:
            worker_skills: List of worker's skills
            job_skills: List of required job skills
            require_exact: If True, only exact matches count
            
        Returns:
            Dict with match score and details
        """
        # Normalize skills
        worker_set = {cls.normalize_skill(s) for s in worker_skills if s.strip()}
        job_set = {cls.normalize_skill(s) for s in job_skills if s.strip()}
        
        if not job_set:
            return {
                'score': 1.0,
                'exact_matches': [],
                'related_matches': [],
                'missing_skills': [],
                'extra_skills': list(worker_set),
            }
        
        # Find exact matches
        exact_matches = worker_set & job_set
        
        # Find related matches
        related_matches = set()
        if not require_exact:
            for job_skill in job_set - exact_matches:
                job_related = cls.get_related_skills(job_skill)
                for worker_skill in worker_set:
                    if worker_skill in job_related:
                        related_matches.add((worker_skill, job_skill))
        
        # Calculate missing skills
        matched_job_skills = exact_matches | {jk for _, jk in related_matches}
        missing_skills = job_set - matched_job_skills
        
        # Calculate score
        exact_score = len(exact_matches) / len(job_set) if job_set else 0
        related_score = (len(related_matches) * 0.7) / len(job_set) if job_set else 0
        
        total_score = min(1.0, exact_score + related_score)
        
        return {
            'score': round(total_score, 3),
            'exact_matches': list(exact_matches),
            'related_matches': [
                {'worker_skill': ws, 'matches_job_skill': js}
                for ws, js in related_matches
            ],
            'missing_skills': list(missing_skills),
            'extra_skills': list(worker_set - exact_matches - {ws for ws, _ in related_matches}),
        }
    
    @classmethod
    def find_matching_workers(
        cls,
        job,
        min_score: float = 0.5,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find workers matching a job based on skills.
        
        Args:
            job: JobRequest instance
            min_score: Minimum match score (0-1)
            limit: Maximum results
            
        Returns:
            List of workers with match scores
        """
        from workers.models import WorkerProfile
        
        # Extract job skills
        job_text = f"{job.title} {job.description}"
        job_skills = cls.extract_skills(job_text)
        
        # Get verified workers
        workers = WorkerProfile.objects.filter(
            is_verified=True
        ).select_related('user')
        
        matches = []
        for worker in workers:
            # Get worker skills
            worker_skills_text = worker.skills if hasattr(worker, 'skills') else ''
            if hasattr(worker, 'bio'):
                worker_skills_text += ' ' + (worker.bio or '')
            
            worker_skills = cls.extract_skills(worker_skills_text)
            
            # Also include manually listed skills
            if worker.skills:
                for skill in worker.skills.split(','):
                    worker_skills.add(cls.normalize_skill(skill))
            
            # Calculate match
            match_result = cls.calculate_skill_match(
                list(worker_skills),
                list(job_skills)
            )
            
            if match_result['score'] >= min_score:
                matches.append({
                    'worker': worker,
                    'match': match_result,
                })
        
        # Sort by score
        matches.sort(key=lambda x: x['match']['score'], reverse=True)
        
        return matches[:limit]
    
    @classmethod
    def find_matching_jobs(
        cls,
        worker_profile,
        min_score: float = 0.3,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find jobs matching a worker's skills.
        
        Args:
            worker_profile: WorkerProfile instance
            min_score: Minimum match score (0-1)
            limit: Maximum results
            
        Returns:
            List of jobs with match scores
        """
        from jobs.models import JobRequest
        
        # Get worker skills
        worker_skills_text = worker_profile.skills if hasattr(worker_profile, 'skills') else ''
        if hasattr(worker_profile, 'bio'):
            worker_skills_text += ' ' + (worker_profile.bio or '')
        
        worker_skills = cls.extract_skills(worker_skills_text)
        
        if worker_profile.skills:
            for skill in worker_profile.skills.split(','):
                worker_skills.add(cls.normalize_skill(skill))
        
        # Get open jobs
        jobs = JobRequest.objects.filter(
            status='open'
        ).exclude(
            applications__worker=worker_profile
        )
        
        matches = []
        for job in jobs:
            job_text = f"{job.title} {job.description}"
            job_skills = cls.extract_skills(job_text)
            
            # Calculate match
            match_result = cls.calculate_skill_match(
                list(worker_skills),
                list(job_skills)
            )
            
            if match_result['score'] >= min_score:
                matches.append({
                    'job': job,
                    'match': match_result,
                })
        
        # Sort by score
        matches.sort(key=lambda x: x['match']['score'], reverse=True)
        
        return matches[:limit]
    
    @classmethod
    def suggest_skills(cls, current_skills: List[str]) -> List[str]:
        """
        Suggest additional skills based on current skills.
        
        Returns skills from the same categories that the worker doesn't have.
        """
        current_normalized = {cls.normalize_skill(s) for s in current_skills if s.strip()}
        
        suggestions = set()
        for skill in current_normalized:
            category = cls.get_skill_category(skill)
            if category:
                # Add other skills from same category
                related = cls.SKILL_CATEGORIES[category]
                suggestions.update(related - current_normalized)
        
        return sorted(suggestions)[:10]
