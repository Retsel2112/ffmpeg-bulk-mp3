class fsm:
    STATE_QUIET = 1
    STATE_LOUD = 2
    STATE_NEITHER = 3
    hrstate = {STATE_QUIET : 'quiet',
               STATE_LOUD : 'loud',
               STATE_NEITHER : 'neither'
              }
    def __init__(self):
        self.thresh_loud = 2200
        self.thresh_quiet = 500
        self.verbose = False
        self.reset()

    def set_verbose(self, verb):
        self.verbose = verb

    def reset(self):
        self.quiets = 0
        self.louds = 0
        self.samples_since_quiet = 0
        self.current_state = fsm.STATE_NEITHER
        self.last_extreme = fsm.STATE_NEITHER
        self.split_ready = False
        self.split_now = False

    def set_loud(self, llev):
        self.thresh_loud = llev
    
    def set_quiet(self, qlev):
        self.thresh_quiet = qlev

    def add_sample(self, val):
        if self.last_extreme != fsm.STATE_QUIET:
            self.samples_since_quiet += 1
        if val < self.thresh_quiet:
            self.current_state = fsm.STATE_QUIET
            self.last_extreme = fsm.STATE_QUIET
            self.quiets += 1
            self.louds = 0
            self.samples_since_quiet = 0
            if self.quiets > 5:
                self.split_ready = True
        elif val > self.thresh_loud:
            self.current_state = fsm.STATE_LOUD
            self.last_extreme = fsm.STATE_LOUD
            self.louds += 1
            if self.louds > 5:
                if self.split_ready:
                    self.split_now = True
                    if self.verbose:
                        print("Should split.")
        else:
            self.current_state = fsm.STATE_NEITHER
            self.louds = 0
            if self.last_extreme != fsm.STATE_LOUD:
                self.samples_since_quiet += 1

        #if val < self.thresh_quiet:
        #    if self.current_state != fsm.STATE_QUIET:
        #        self.current_state = fsm.STATE_QUIET
        #elif val > self.thresh_loud:
        #    if self.current_state != fsm.STATE_LOUD:
        #        self.current_state = fsm.STATE_LOUD
        #else:
        #    if val < self.thresh_loud:
        #        self.current_state = fsm.STATE_NEITHER
        
    def should_split(self):
        return self.split_now

    def get_state(self):
        return fsm.hrstate[self.current_state]

    def last_quiet(self):
        return self.samples_since_quiet
