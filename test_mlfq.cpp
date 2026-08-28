#include <iostream>
#include <vector>
#include <string>
#include <iomanip>
#include <algorithm>

using namespace std;

struct Process {
    string pid;
    int at;
    int bt;
    int rem_bt;
    int ct;
    int tat;
    int wt;
    int rt;
    int first_run_time;
    int completed_in_q;

    Process(string id, int a, int b) 
        : pid(id), at(a), bt(b), rem_bt(b), ct(0), tat(0), wt(0), rt(-1), first_run_time(-1), completed_in_q(-1) {}
};

void printQueue(const string& qName, const vector<Process*>& q) {
    cout << qName << "=[";
    for (size_t i = 0; i < q.size(); ++i) {
        cout << q[i]->pid << (i + 1 < q.size() ? ", " : "");
    }
    cout << "]";
}

void printAllQueues(const vector<Process*>& q1, const vector<Process*>& q2, const vector<Process*>& q3) {
    printQueue("Q1", q1);
    cout << ", ";
    printQueue("Q2", q2);
    cout << ", ";
    printQueue("Q3", q3);
    cout << endl;
}

void simulate(int tq1, int tq2, vector<Process>& proc_list) {
    vector<Process*> q1, q2, q3;
    int current_time = 0;
    int completed = 0;
    int n = proc_list.size();
    
    vector<Process*> unarrived;
    for (auto& p : proc_list) unarrived.push_back(&p);

    cout << "\n=======================================================\n";
    cout << "    MLFQ SIMULATION (Q1 TQ = " << tq1 << ", Q2 TQ = " << tq2 << ")\n";
    cout << "=======================================================\n\n";

    Process* current = nullptr;
    int curr_q = 0;
    int time_slice = 0;

    vector<string> demoted_q1_q2, demoted_q2_q3;
    vector<string> completed_q1, completed_q2, completed_q3;

    while (completed < n) {
        // 1. Check arrivals at current_time
        auto it = unarrived.begin();
        while (it != unarrived.end()) {
            if ((*it)->at == current_time) {
                q1.push_back(*it);
                cout << "[Time " << setw(2) << current_time << "] Process " << (*it)->pid << " arrived -> added to Q1. Queue state: ";
                printAllQueues(q1, q2, q3);
                it = unarrived.erase(it);
            } else {
                ++it;
            }
        }

        // 2. Preemption check if a process is running in lower queue and higher queue has processes
        if (current != nullptr && curr_q > 1 && !q1.empty()) {
            cout << "[Time " << setw(2) << current_time << "] PREEMPTION! Process " << current->pid << " preempted from Q" << curr_q << " by newly arrived process in Q1.\n";
            if (curr_q == 2) q2.insert(q2.begin(), current);
            else if (curr_q == 3) q3.insert(q3.begin(), current);
            current = nullptr;
            curr_q = 0;
            time_slice = 0;
        }

        // 3. Select next process if CPU is idle
        if (current == nullptr) {
            if (!q1.empty()) {
                current = q1.front(); q1.erase(q1.begin());
                curr_q = 1;
                time_slice = tq1;
            } else if (!q2.empty()) {
                current = q2.front(); q2.erase(q2.begin());
                curr_q = 2;
                time_slice = tq2;
            } else if (!q3.empty()) {
                current = q3.front(); q3.erase(q3.begin());
                curr_q = 3;
                time_slice = 1e9; // infinity for FCFS
            }

            if (current != nullptr) {
                if (current->first_run_time == -1) {
                    current->first_run_time = current_time;
                    current->rt = current->first_run_time - current->at;
                }
                cout << "[Time " << setw(2) << current_time << "] Scheduling Decision: Selected " << current->pid << " from Q" << curr_q << ". Queue state: ";
                printAllQueues(q1, q2, q3);
            }
        }

        // 4. Execute 1 time unit
        if (current != nullptr) {
            current->rem_bt--;
            time_slice--;
            current_time++;

            // Check arrivals during this step
            auto it2 = unarrived.begin();
            while (it2 != unarrived.end()) {
                if ((*it2)->at == current_time) {
                    q1.push_back(*it2);
                    cout << "[Time " << setw(2) << current_time << "] Process " << (*it2)->pid << " arrived -> added to Q1. Queue state: ";
                    printAllQueues(q1, q2, q3);
                    it2 = unarrived.erase(it2);
                } else {
                    ++it2;
                }
            }

            // Check completion or quantum expiry
            if (current->rem_bt == 0) {
                current->ct = current_time;
                current->tat = current->ct - current->at;
                current->wt = current->tat - current->bt;
                current->completed_in_q = curr_q;

                if (curr_q == 1) completed_q1.push_back(current->pid);
                else if (curr_q == 2) completed_q2.push_back(current->pid);
                else if (curr_q == 3) completed_q3.push_back(current->pid);

                cout << "[Time " << setw(2) << current_time << "] Event: Process " << current->pid << " COMPLETED in Q" << curr_q << "! CT=" << current->ct << ". Queue state: ";
                printAllQueues(q1, q2, q3);
                completed++;
                current = nullptr;
                curr_q = 0;
                time_slice = 0;
            } else if (time_slice == 0) {
                if (curr_q == 1) {
                    q2.push_back(current);
                    demoted_q1_q2.push_back(current->pid);
                    cout << "[Time " << setw(2) << current_time << "] Event: Process " << current->pid << " TQ expired in Q1 -> Demoted to Q2. Queue state: ";
                } else if (curr_q == 2) {
                    q3.push_back(current);
                    demoted_q2_q3.push_back(current->pid);
                    cout << "[Time " << setw(2) << current_time << "] Event: Process " << current->pid << " TQ expired in Q2 -> Demoted to Q3. Queue state: ";
                }
                printAllQueues(q1, q2, q3);
                current = nullptr;
                curr_q = 0;
            }
        } else {
            current_time++;
        }
    }

    // Print Tabular Results
    cout << "\n--------------------------------------------------------------------------------\n";
    cout << left << setw(8) << "Process" << setw(8) << "AT" << setw(8) << "BT" << setw(8) << "CT" 
         << setw(8) << "TAT" << setw(8) << "WT" << setw(8) << "RT" << setw(15) << "Completed In" << "\n";
    cout << "--------------------------------------------------------------------------------\n";

    double total_tat = 0, total_wt = 0, total_rt = 0;
    for (const auto& p : proc_list) {
        cout << left << setw(8) << p.pid << setw(8) << p.at << setw(8) << p.bt << setw(8) << p.ct 
             << setw(8) << p.tat << setw(8) << p.wt << setw(8) << p.rt << "Q" << p.completed_in_q << "\n";
        total_tat += p.tat;
        total_wt += p.wt;
        total_rt += p.rt;
    }
    cout << "--------------------------------------------------------------------------------\n";
    cout << fixed << setprecision(2);
    cout << "Average Turnaround Time : " << total_tat / n << " units\n";
    cout << "Average Waiting Time    : " << total_wt / n << " units\n";
    cout << "Average Response Time   : " << total_rt / n << " units\n";
    cout << "--------------------------------------------------------------------------------\n";

    // Process Classification Summary
    cout << "\nProcess Classification Breakdown:\n";
    cout << "  - Completed in Q1            : ";
    if (completed_q1.empty()) cout << "None";
    else for (size_t i = 0; i < completed_q1.size(); ++i) cout << completed_q1[i] << (i + 1 < completed_q1.size() ? ", " : "");
    cout << "\n  - Demoted from Q1 to Q2      : ";
    for (size_t i = 0; i < demoted_q1_q2.size(); ++i) cout << demoted_q1_q2[i] << (i + 1 < demoted_q1_q2.size() ? ", " : "");
    cout << "\n  - Completed in Q2            : ";
    for (size_t i = 0; i < completed_q2.size(); ++i) cout << completed_q2[i] << (i + 1 < completed_q2.size() ? ", " : "");
    cout << "\n  - Demoted from Q2 to Q3      : ";
    for (size_t i = 0; i < demoted_q2_q3.size(); ++i) cout << demoted_q2_q3[i] << (i + 1 < demoted_q2_q3.size() ? ", " : "");
    cout << "\n  - Completed in Q3            : ";
    for (size_t i = 0; i < completed_q3.size(); ++i) cout << completed_q3[i] << (i + 1 < completed_q3.size() ? ", " : "");
    cout << "\n\n";
}

int main() {
    vector<Process> base_processes = {
        {"P1", 0, 15},
        {"P2", 1, 6},
        {"P3", 2, 12},
        {"P4", 3, 5},
        {"P5", 4, 8},
        {"P6", 5, 3},
        {"P7", 6, 10},
        {"P8", 7, 4}
    };

    cout << "Multilevel Feedback Queue (MLFQ) Simulator\n";
    
    // Run Configuration 1
    auto proc1 = base_processes;
    simulate(2, 4, proc1);

    // Run Configuration 2
    auto proc2 = base_processes;
    simulate(3, 5, proc2);

    return 0;
}
