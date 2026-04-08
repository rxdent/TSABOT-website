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

        #---------------Create a new topic-----------------------
        stats = self.data["topics"].setdefault(topic_id, {"correct": 0, "incorrect": 0})
        
        #-------------------Update--------------------
        if is_correct: stats["correct"] += 1
        else: stats["incorrect"] += 1
        
        #-----------------Weak Topics-----------------
        total = stats["correct"] + stats["incorrect"]
        percentage = (stats["correct"] / total) * 100
        
        if percentage < 70 and topic_id not in self.data["weak_topics"]:
            self.data["weak_topics"].append(topic_id)
        elif percentage >= 70 and topic_id in self.data["weak_topics"]:
            self.data["weak_topics"].remove(topic_id)

        self.save()

        #--------------Show weak topics-----------------
    def show_weak(self):
        print("\n--- Review These Sections ---")
        if not self.data["weak_topics"]:
            print("Everything looks good! No weak topics.")
        for tid in self.data["weak_topics"]:
            print(f"• {unit_manager.get_name(tid)}")