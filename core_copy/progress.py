import json
import os
from core_copy.units import UnitManager

unit_manager = UnitManager()

class ProgressManager:
    def __init__(self, progress_file="progress.json"):
        self.p_file = progress_file

        if os.path.exists(self.p_file): #if file already exists, open it.
             try:
                with open(self.p_file, "r") as f:
                    self.data = json.load(f)
             except json.JSONDecodeError:
                 self.data = {"topics": {}, "weak_topics": []} #if it doesn't exist or error shows, create a new file.
        else:
             self.data = {"topics": {}, "weak_topics": []}

    def save(self):
        with open(self.p_file, "w") as f:
            json.dump(self.data, f, indent=4)

    def update(self, topic_id, is_correct):
            # 1. Ensure the topic exists in our data dictionary
            if topic_id not in self.data["topics"]:
                self.data["topics"][topic_id] = {"correct": 0, "incorrect": 0}
            
            stats = self.data["topics"][topic_id]
            
            # 2. Update the counts
            if is_correct: 
                stats["correct"] += 1
            else: 
                stats["incorrect"] += 1
            
            # 3. Calculate the new mastery percentage
            total = stats["correct"] + stats["incorrect"]
            percentage = (stats["correct"] / total) * 100
            
            # 4. Update Weak Topics using set logic for accuracy
            # We convert to a set temporarily to make adding/removing cleaner
            weak_set = set(self.data.get("weak_topics", []))
            
            if percentage < 70:
                weak_set.add(topic_id)
            else:
                if topic_id in weak_set:
                    weak_set.remove(topic_id)

            # Convert back to list for JSON storage
            self.data["weak_topics"] = list(weak_set)

            # 5. Save changes immediately
            self.save()

        #--------------Show weak topics-----------------
    def show_weak(self):
        print("\n--- Review These Sections ---")
        if not self.data["weak_topics"]:
            print("Everything looks good! No weak topics.")
        for tid in self.data["weak_topics"]:
            print(f"• {unit_manager.get_name(tid)}")