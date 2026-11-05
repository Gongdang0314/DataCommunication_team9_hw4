HW#4 rule_test kit (10 x 10 boards)

All boards: 10 lines x 10 chars, spaces are real spaces, LF line endings.
Small boards are also TORUS (rows mod 10, cols mod 10).

[Rule1]  rule1_input.txt -> rule1_output_R1.txt / _R2 / _R3 / _R10 (after 1, 2, 3, 10 Rounds)
         rule1_WRONG_inplace_R1.txt : what you get if you update in place (WRONG, do not match this)
[Rule2]  rule2_input.txt -> rule2_output_R1.txt / _R2 / _R3
[Rule3]  rule3_input.txt -> rule3_output_R1.txt / _R2 / _R10 (R10 == input: period 10)
[Repaint at Round 1000]
         repaint_S1000.txt + repaint_canvas1.txt
           -> repaint_step1_painted.txt   (copy canvas1 chars except ' ' and '.')
           -> repaint_step2_brian.txt     (every non-space -> '@')
           -> repaint_step3_R1000.txt     (Rule2, 1 Round)
[Rule3 conversion at Round 2000]
         cyclic_convert_input.txt -> cyclic_convert_output_y25_team11.txt
           (first line is original row y = 25, team = 11)
[Band test, N = 3 on rule1_input.txt]   bands rows [0,3) [3,6) [6,10)
         band_N3_Wk_work.txt   = top halo + band + bottom halo
         band_N3_Wk_output.txt = Rule1 result of the band rows only
         W0 + W1 + W2 outputs joined == rule1_output_R1.txt
tests.txt : all Rule tests in one file for a test runner ('·' = space)

Compare:  Linux/macOS  diff my_out.txt rule1_output_R1.txt && echo PASS
          Windows      fc my_out.txt rule1_output_R1.txt

This kit is for self-checking only. Test results are NOT submitted.
Submit hash_result.txt instead (see section 6-3 of HW4description.pdf).

Test runner (same program in 3 languages: python/, java/, c/) - run it IN THIS KIT FOLDER
  myrules.*    : template - implement YOUR cell functions here:
                 rule1_cell / rule2_cell / rule3_cell(w, i, x), repaint(w, c), to_brian(w), to_cyclic(w, ytop, team)
                 A cell function reads rows i-1 and i+1 as they are (NO vertical wrap) and wraps columns (x +- 1) % W.
                 band   : (h+2)-row working board -> middle h rows  (= what a Worker computes)
                 whole  : full board with vertical Torus (last/first row added as halo)
  rule_test.*  : (no args)                                      all tests in tests.txt (Step 1-6)
                 rule1_input.txt 1 10 my_R10.txt                board file: input rule rounds output
                 band band_N3_W0_work.txt 1 my_W0.txt           band (Step 9)
                 repaint repaint_S1000.txt repaint_canvas1.txt my_s1.txt   (Step 7)
                 brian repaint_step1_painted.txt my_s2.txt                 (Step 7)
                 cyclic cyclic_convert_input.txt 25 11 my_c.txt            (Step 8)

  Python 3 : python python/rule_test.py [args]
  Java 8+  : javac -encoding UTF-8 java/rule_test.java java/myrules.java
             java -cp java rule_test [args]
  ANSI C   : gcc -std=c89 -Wall -o rule_test c/rule_test.c c/myrules.c      (myrules.h in c/)
             ./rule_test [args]          (Windows: rule_test [args])
  Until myrules is implemented, the runner stops with "not implemented yet".
  Then compare each output with the answer file (diff / fc).
