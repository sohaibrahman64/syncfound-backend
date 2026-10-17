---
name: fix-relationship-backpopulates-userprofile-model
description: Corrected incorrect back_populates values for user_skills, cofounder_skills, industries, and location_preferences relationships in UserProfile model
metadata:
  type: project
---

Fixed incorrect back_populates values in the UserProfile model relationships. The back_populates value should be the name of the attribute on the OTHER class that points back to this class.

**Changes Made:**
- `user_skills` relationship: changed `back_populates="user_skills"` to `back_populates="user_profile"`
- `cofounder_skills` relationship: changed `back_populates="cofounder_skills"` to `back_populates="user_profile"`
- `industries` relationship: changed `back_populates="industries"` to `back_populates="user_profile"`
- `location_preferences` relationship: changed `back_populates="location_preferences"` to `back_populates="user_profile"`

**Why:** The original values were incorrect, causing SQLAlchemy mapper initialization errors. The back_populates value must match the name of the reverse relationship attribute on the related model.

**How to apply:** Ensure that for each bidirectional relationship, the back_populates value in each model points to the correct attribute name on the other model.